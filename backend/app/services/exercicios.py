"""Exercícios de prática de um módulo, gerados pela IA a partir do vault (#201).

O aluno abre o passo e pede para praticar: os exercícios do módulo para o nível
dele saem da tabela, se já foram gerados, ou entram na fila para gerar. A
geração usa só os trechos do vault daquele módulo:

- módulo feito de uma parte de vídeo (#210): os trechos da transcrição do vídeo
  que terminam dentro do intervalo do módulo;
- módulo do catálogo: a transcrição do vídeo dele (`modulo:<id>`) e o texto do
  módulo (`descricao:modulo:<id>`).

Sem trecho, não há geração (`sem_conteudo`): o exercício seria inventado.
"""

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ia import IAIndisponivel, ProvedorIA
from app.ia.skills import exercicios as skill
from app.models import (
    DocumentoVault,
    ExerciciosGerados,
    Modulo,
    NivelExperiencia,
    StatusGeracao,
)

logger = logging.getLogger(__name__)

ERRO_SAIDA_INVALIDA = "A IA não devolveu os exercícios no formato pedido."


def pedir(db: Session, modulo: Modulo, nivel: NivelExperiencia) -> tuple[ExerciciosGerados, bool]:
    """Os exercícios do módulo para o nível. `True` se é preciso pôr a geração na fila.

    A geração que falhou é refeita no pedido seguinte; a que está gerando, pronta
    ou sem conteúdo, não.
    """
    geracao = db.scalar(
        select(ExerciciosGerados).where(
            ExerciciosGerados.modulo_id == modulo.id, ExerciciosGerados.nivel == nivel
        )
    )
    if geracao is not None and geracao.status is not StatusGeracao.falhou:
        return geracao, False
    if geracao is None:
        try:
            with db.begin_nested():
                geracao = ExerciciosGerados(modulo_id=modulo.id, nivel=nivel)
                db.add(geracao)
        except IntegrityError:
            # Dois alunos do mesmo nível ao mesmo tempo: o outro já criou.
            return pedir(db, modulo, nivel)
    else:
        geracao.status = StatusGeracao.gerando
        geracao.erro = None
    db.commit()
    return geracao, True


async def gerar(db: Session, provedor: ProvedorIA, geracao: ExerciciosGerados) -> None:
    """Gera e grava. A IA fora do ar estoura, para a fila tentar de novo."""
    modulo = db.get(Modulo, geracao.modulo_id)
    conteudo = conteudo_do_modulo(db, modulo) if modulo else []
    if not conteudo:
        geracao.status = StatusGeracao.sem_conteudo
        db.commit()
        return
    try:
        pedacos = [
            pedaco
            async for pedaco in provedor.gerar(
                skill.mensagens(modulo.titulo, geracao.nivel, conteudo),
                max_tokens=skill.MAXIMO_DE_TOKENS,
                formato=skill.FORMATO,
            )
        ]
        lista = skill.ler_resposta("".join(pedacos))
    except skill.SaidaInvalida:
        logger.warning("Exercícios inválidos para o módulo %s", modulo.id)
        geracao.status = StatusGeracao.falhou
        geracao.erro = ERRO_SAIDA_INVALIDA
        db.commit()
        return
    except IAIndisponivel:
        geracao.status = StatusGeracao.falhou
        geracao.erro = "A IA estava fora do ar."
        db.commit()
        raise
    geracao.exercicios = [exercicio.model_dump() for exercicio in lista.exercicios]
    geracao.status = StatusGeracao.pronto
    db.commit()


def conteudo_do_modulo(db: Session, modulo: Modulo) -> list[str]:
    """Os textos do vault que o módulo ensina, na ordem do vídeo."""
    parte = modulo.parte_video
    if parte is not None:
        documento = db.scalar(
            select(DocumentoVault).where(DocumentoVault.video_id == parte.video_id)
        )
        if documento is None:
            return []
        # Cada trecho conta para o intervalo em que termina (ver a categorização).
        return [
            trecho.texto
            for trecho in documento.trechos
            if parte.inicio_segundos
            < (trecho.fim_segundos or trecho.inicio_segundos or 0)
            <= parte.fim_segundos
        ]
    documentos = db.scalars(
        select(DocumentoVault)
        .where(DocumentoVault.chave.in_([f"modulo:{modulo.id}", f"descricao:modulo:{modulo.id}"]))
        .order_by(DocumentoVault.chave.desc())
    )
    return [trecho.texto for documento in documentos for trecho in documento.trechos]
