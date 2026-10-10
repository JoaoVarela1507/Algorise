"""Correção das atividades e registro das tentativas (telas 28 a 38).

Três regras mandam aqui:

- **a correção é do servidor.** O gabarito nunca sai da API antes da submissão
  (`AtividadeResumo` não tem os campos de resposta), e quem diz se acertou é
  esta camada, não o cliente;
- **toda tentativa é guardada**, não só a última: é o que permite ao aluno
  retomar de onde parou e é a base das métricas de aprendizado;
- **XP por atividade sai uma vez só.** Reenviar a resposta certa não paga de
  novo — a checagem é a existência de uma tentativa correta anterior.
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Atividade,
    Modulo,
    OrigemXP,
    RespostaUsuario,
    TipoAtividade,
    Trilha,
    Usuario,
)
from app.services import progresso, xp


class TipoNaoSuportado(Exception):
    """Tipo de atividade que ainda não tem correção escrita."""


class AtividadesPendentes(Exception):
    """Ainda falta acertar atividade deste passo."""


@dataclass(frozen=True)
class Correcao:
    """O que a correção decidiu, antes de virar resposta HTTP."""

    correta: bool
    # `True` quando a resposta ficou guardada esperando correção por IA (#11).
    em_analise: bool
    feedback: str


# Tipos que já sabemos corrigir sozinhos. Os outros (múltipla escolha,
# ordenação, lacuna, desafio) precisam de campos que o modelo ainda não tem:
# alternativas, ordem esperada, posição da lacuna. Entram com as telas deles.
TIPOS_CORRIGIVEIS = {TipoAtividade.terminal, TipoAtividade.resposta_aberta}

# Mínimo para uma resposta aberta ser considerada uma tentativa de verdade, e
# não um "sei lá" para destravar a tela.
MINIMO_RESPOSTA_ABERTA = 20

# Bônus por fechar o passo, além do XP de cada atividade. A curva de níveis e as
# demais regras de pontuação são a #31.
XP_POR_PASSO = 20


def normalizar_comando(texto: str) -> str:
    """`  python   --VERSION ` e `python --version` são o mesmo comando.

    O aluno está digitando num terminal, não preenchendo um campo: espaço
    sobrando e maiúscula não são erro de conteúdo.
    """
    return " ".join(texto.split()).lower()


def corrigir(atividade: Atividade, conteudo: str) -> Correcao:
    """Decide se a resposta está certa. Não toca no banco — é só a regra."""
    if atividade.tipo not in TIPOS_CORRIGIVEIS:
        raise TipoNaoSuportado(atividade.tipo)

    if atividade.tipo is TipoAtividade.terminal:
        esperado = normalizar_comando(atividade.comando_esperado or "")
        acertou = bool(esperado) and normalizar_comando(conteudo) == esperado
        return Correcao(
            correta=acertou,
            em_analise=False,
            feedback=(
                "Comando correto!"
                if acertou
                else "Esse não é o comando que a atividade pede. Confira a dica e tente de novo."
            ),
        )

    # Resposta aberta: quem corrige é a IA (#11), que ainda não existe. Guardar
    # e marcar como em análise é mais honesto do que inventar um acerto — e não
    # paga XP, para ninguém ganhar ponto por texto que ninguém leu.
    if len(conteudo.strip()) < MINIMO_RESPOSTA_ABERTA:
        return Correcao(
            correta=False,
            em_analise=False,
            feedback=(f"Escreva um pouco mais: pelo menos {MINIMO_RESPOSTA_ABERTA} caracteres."),
        )

    return Correcao(
        correta=False,
        em_analise=True,
        feedback="Resposta recebida. A correção automática desta atividade ainda está a caminho.",
    )


def submeter(
    db: Session,
    *,
    usuario: Usuario,
    atividade: Atividade,
    trilha_id: int | None = None,
    conteudo: str,
    tempo_gasto_segundos: int | None = None,
) -> tuple[RespostaUsuario, Correcao, int]:
    """Corrige, grava a tentativa e concede o XP quando é o primeiro acerto.

    Devolve a tentativa gravada, a correção e o XP ganho **nesta** submissão —
    zero quando o aluno já tinha acertado antes.
    """
    correcao = corrigir(atividade, conteudo)
    ja_tinha_acertado = _acertou_antes(db, usuario_id=usuario.id, atividade_id=atividade.id)

    tentativa = RespostaUsuario(
        usuario_id=usuario.id,
        atividade_id=atividade.id,
        tentativa=_proxima_tentativa(db, usuario_id=usuario.id, atividade_id=atividade.id),
        conteudo=conteudo,
        correta=correcao.correta,
        tempo_gasto_segundos=tempo_gasto_segundos,
        feedback=correcao.feedback,
    )
    db.add(tentativa)
    db.commit()

    if not correcao.correta or ja_tinha_acertado:
        return tentativa, correcao, 0

    xp.registrar_xp(
        db,
        usuario_id=usuario.id,
        valor=atividade.xp,
        origem=OrigemXP.atividade,
        referencia_id=atividade.id,
        trilha_id=trilha_id,
    )
    return tentativa, correcao, atividade.xp


def tentativas(db: Session, *, usuario_id: int, atividade_id: int) -> list[RespostaUsuario]:
    """As tentativas do aluno nesta atividade, da mais antiga para a mais nova."""
    return list(
        db.execute(
            select(RespostaUsuario)
            .where(
                RespostaUsuario.usuario_id == usuario_id,
                RespostaUsuario.atividade_id == atividade_id,
            )
            .order_by(RespostaUsuario.tentativa)
        ).scalars()
    )


def concluir_passo(
    db: Session, *, usuario: Usuario, trilha: Trilha, modulo: Modulo
) -> tuple[int, int | None]:
    """Fecha o passo e devolve o XP ganho agora e a ordem do próximo.

    O XP das atividades já foi pago na submissão de cada uma; aqui entra o bônus
    do passo, uma vez só. Fechar duas vezes não paga de novo.
    """
    pendentes = [
        atividade
        for atividade in modulo.atividades
        if atividade.tipo in TIPOS_CORRIGIVEIS
        and atividade.tipo is not TipoAtividade.resposta_aberta
        and not _acertou_antes(db, usuario_id=usuario.id, atividade_id=atividade.id)
    ]
    if pendentes:
        raise AtividadesPendentes(len(pendentes))

    ja_concluido = progresso.esta_concluido(db, usuario_id=usuario.id, modulo_id=modulo.id)
    progresso.concluir_passo(db, usuario_id=usuario.id, trilha=trilha, modulo=modulo)

    ganho = 0
    if not ja_concluido:
        ganho = XP_POR_PASSO
        xp.registrar_xp(
            db,
            usuario_id=usuario.id,
            valor=ganho,
            origem=OrigemXP.modulo,
            referencia_id=modulo.id,
            trilha_id=trilha.id,
        )

    ordens = sorted(m.ordem for m in trilha.modulos)
    proximo = next((ordem for ordem in ordens if ordem > modulo.ordem), None)
    return ganho, proximo


def _acertou_antes(db: Session, *, usuario_id: int, atividade_id: int) -> bool:
    return (
        db.execute(
            select(RespostaUsuario.id)
            .where(
                RespostaUsuario.usuario_id == usuario_id,
                RespostaUsuario.atividade_id == atividade_id,
                RespostaUsuario.correta.is_(True),
            )
            .limit(1)
        ).scalar()
        is not None
    )


def _proxima_tentativa(db: Session, *, usuario_id: int, atividade_id: int) -> int:
    ultima = db.execute(
        select(func.max(RespostaUsuario.tentativa)).where(
            RespostaUsuario.usuario_id == usuario_id,
            RespostaUsuario.atividade_id == atividade_id,
        )
    ).scalar()
    return (ultima or 0) + 1
