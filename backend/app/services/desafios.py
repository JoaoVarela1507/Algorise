"""Desafio de código (#34): enunciado, execução na sandbox e correção pelos casos.

A API só grava a execução e enfileira; quem roda é o worker
(`tarefas/execucao.py`), que chama `executar` aqui. Cada caso de teste é um
container novo (`app/sandbox`): o estado de um não vaza para o outro.

**Correção:** a saída bate com a esperada ignorando espaço no fim das linhas e
linhas em branco no fim, que é como o aluno vê no terminal. O primeiro caso que
falha encerra a execução: rodar o resto só gastaria container.

**Relatório:** caso público mostra entrada, esperado e obtido; caso oculto só
diz se passou.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Atividade, CasoDeTeste, Execucao, StatusExecucao, TipoAtividade, Usuario
from app.sandbox import Resultado, SandboxIndisponivel
from app.sandbox import executar as rodar_na_sandbox
from app.services import submissoes

logger = logging.getLogger(__name__)


class DesafioNaoEncontrado(Exception):
    """A atividade não existe ou não é um desafio de código."""


class ExecucaoNaoEncontrada(Exception):
    """A execução não existe ou é de outro aluno."""


def obter(db: Session, atividade_id: int) -> Atividade:
    atividade = db.get(Atividade, atividade_id)
    if atividade is None or atividade.tipo is not TipoAtividade.desafio_codigo:
        raise DesafioNaoEncontrado
    return atividade


def casos(db: Session, atividade_id: int, *, so_publicos: bool = False) -> list[CasoDeTeste]:
    consulta = select(CasoDeTeste).where(CasoDeTeste.atividade_id == atividade_id)
    if so_publicos:
        consulta = consulta.where(CasoDeTeste.publico.is_(True))
    return list(db.scalars(consulta.order_by(CasoDeTeste.ordem)))


def criar_execucao(db: Session, usuario: Usuario, atividade: Atividade, codigo: str) -> Execucao:
    execucao = Execucao(
        id=uuid.uuid4().hex,
        usuario_id=usuario.id,
        atividade_id=atividade.id,
        codigo=codigo,
        status=StatusExecucao.na_fila,
        stdout="",
        stderr="",
        casos=[],
    )
    db.add(execucao)
    db.commit()
    return execucao


def do_aluno(db: Session, usuario: Usuario, execucao_id: str) -> Execucao:
    execucao = db.get(Execucao, execucao_id)
    if execucao is None or execucao.usuario_id != usuario.id:
        raise ExecucaoNaoEncontrada
    return execucao


def executar(db: Session, execucao_id: str) -> None:
    """Roda os casos na sandbox e grava o resultado. Chamado pelo worker."""
    execucao = db.get(Execucao, execucao_id)
    if execucao is None or execucao.status is not StatusExecucao.na_fila:
        return
    execucao.status = StatusExecucao.executando
    db.commit()

    relatorio: list[dict[str, Any]] = []
    ultimo: Resultado | None = None
    aprovada = True
    try:
        for caso in casos(db, execucao.atividade_id):
            ultimo = rodar_na_sandbox(execucao.codigo, caso.entrada)
            passou, motivo = _conferir(ultimo, caso.saida_esperada)
            relatorio.append(_linha(caso, ultimo, passou, motivo))
            if not passou:
                aprovada = False
                break
    except SandboxIndisponivel as erro:
        logger.error("Sandbox indisponível na execução %s: %s", execucao_id, erro)
        _terminar(db, execucao, StatusExecucao.falhou, erro="A correção está fora do ar agora.")
        return

    execucao.casos = relatorio
    execucao.stdout = ultimo.stdout if ultimo else ""
    execucao.stderr = ultimo.stderr if ultimo else ""
    # Desafio sem caso nenhum não tem como ser aprovado: seria XP de graça.
    execucao.aprovada = aprovada and bool(relatorio)
    _terminar(db, execucao, StatusExecucao.concluida)
    if execucao.aprovada:
        usuario = db.get_one(Usuario, execucao.usuario_id)
        atividade = db.get_one(Atividade, execucao.atividade_id)
        submissoes.registrar_acerto(
            db, usuario=usuario, atividade=atividade, conteudo=execucao.codigo
        )


def falhar(db: Session, execucao_id: str, motivo: str) -> None:
    """O job morreu no worker (timeout do RQ, worker derrubado)."""
    execucao = db.get(Execucao, execucao_id)
    if execucao is not None and execucao.status in (
        StatusExecucao.na_fila,
        StatusExecucao.executando,
    ):
        _terminar(db, execucao, StatusExecucao.falhou, erro=motivo[:300])


def normalizar_saida(texto: str) -> str:
    linhas = [linha.rstrip() for linha in texto.replace("\r\n", "\n").split("\n")]
    while linhas and not linhas[-1]:
        linhas.pop()
    return "\n".join(linhas)


def _conferir(resultado: Resultado, esperado: str) -> tuple[bool, str | None]:
    if resultado.tempo_esgotado:
        return False, "tempo_esgotado"
    if resultado.memoria_estourada:
        return False, "memoria_estourada"
    if resultado.saida_cortada:
        return False, "saida_grande_demais"
    if resultado.codigo_saida != 0:
        return False, "erro_de_execucao"
    if normalizar_saida(resultado.stdout) != normalizar_saida(esperado):
        return False, "saida_diferente"
    return True, None


def _linha(
    caso: CasoDeTeste, resultado: Resultado, passou: bool, motivo: str | None
) -> dict[str, Any]:
    linha: dict[str, Any] = {
        "ordem": caso.ordem,
        "publico": caso.publico,
        "passou": passou,
        "motivo": motivo,
    }
    if caso.publico:
        linha |= {
            "entrada": caso.entrada,
            "esperado": caso.saida_esperada,
            "obtido": resultado.stdout,
        }
    return linha


def _terminar(
    db: Session, execucao: Execucao, status: StatusExecucao, *, erro: str | None = None
) -> None:
    execucao.status = status
    execucao.erro = erro
    execucao.terminada_em = datetime.now(UTC)
    db.commit()
