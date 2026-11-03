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

import json
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
    XPEvento,
)
from app.services import certificados, progresso, xp


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


# Tipos que já sabemos corrigir sozinhos. O desafio de código precisa rodar o
# programa do aluno, e isso ainda não existe.
TIPOS_CORRIGIVEIS = {
    TipoAtividade.terminal,
    TipoAtividade.resposta_aberta,
    TipoAtividade.multipla_escolha,
    TipoAtividade.ordenacao,
    TipoAtividade.preencher_lacuna,
}

# Mínimo para uma resposta aberta ser considerada uma tentativa de verdade, e
# não um "sei lá" para destravar a tela.
MINIMO_RESPOSTA_ABERTA = 20

# Bônus por fechar o passo, além do XP de cada atividade. A curva de níveis e as
# demais regras de pontuação são a #31.
XP_POR_PASSO = 20
# Bônus de concluir a trilha inteira, uma vez só (telas 38 e 41).
XP_POR_TRILHA = 40


def normalizar_comando(texto: str) -> str:
    """`  python   --VERSION ` e `python --version` são o mesmo comando.

    O aluno está digitando num terminal, não preenchendo um campo: espaço
    sobrando e maiúscula não são erro de conteúdo.
    """
    return " ".join(texto.split()).lower()


def _normalizar_texto(texto: str | None) -> str:
    """Espaço sobrando nas pontas e no meio não é erro de conteúdo."""
    return " ".join((texto or "").split())


def _lista(texto: str | None) -> list[str]:
    """Uma lista JSON de textos. Qualquer outra coisa vira lista vazia, que nunca acerta."""
    try:
        valor = json.loads(texto or "")
    except ValueError:
        return []
    if not isinstance(valor, list):
        return []
    return [str(item) for item in valor]


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

    if atividade.tipo is TipoAtividade.multipla_escolha:
        acertou = _normalizar_texto(conteudo) == _normalizar_texto(atividade.resposta_esperada)
        return Correcao(
            correta=acertou,
            em_analise=False,
            feedback="Isso mesmo!" if acertou else "Não é essa. Releia o enunciado e tente outra.",
        )

    if atividade.tipo is TipoAtividade.ordenacao:
        esperado = _lista(atividade.resposta_esperada)
        enviado = _lista(conteudo)
        acertou = bool(esperado) and [_normalizar_texto(i) for i in enviado] == [
            _normalizar_texto(i) for i in esperado
        ]
        return Correcao(
            correta=acertou,
            em_analise=False,
            feedback=(
                "Ordem certa!"
                if acertou
                else "Quase: alguma linha está fora do lugar. Pense no que precisa vir antes."
            ),
        )

    if atividade.tipo is TipoAtividade.preencher_lacuna:
        esperado = _lista(atividade.resposta_esperada)
        enviado = _lista(conteudo)
        certas = sum(
            1
            for resposta, gabarito in zip(enviado, esperado, strict=False)
            # Sem baixar a caixa, como no terminal: em código `True` e `true`
            # são coisas diferentes.
            if _normalizar_texto(resposta) == _normalizar_texto(gabarito)
        )
        acertou = bool(esperado) and len(enviado) == len(esperado) and certas == len(esperado)
        return Correcao(
            correta=acertou,
            em_analise=False,
            feedback=(
                "Todas as lacunas certas!"
                if acertou
                else "Ainda não é isso. Confira a lacuna."
                if len(esperado) == 1
                else f"{certas} de {len(esperado)} lacunas certas. Confira as outras."
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
    # Fechou o último passo de uma trilha de parceiro: sai o certificado (#32).
    certificados.emitir_se_concluiu(db, usuario, trilha)

    ganho = 0
    if not ja_concluido:
        ganho = XP_POR_PASSO
        xp.registrar_xp(
            db,
            usuario_id=usuario.id,
            valor=ganho,
            origem=OrigemXP.modulo,
            referencia_id=modulo.id,
        )

        ganho += _bonus_da_trilha(db, usuario_id=usuario.id, trilha=trilha)

    ordens = sorted(m.ordem for m in trilha.modulos)
    proximo = next((ordem for ordem in ordens if ordem > modulo.ordem), None)
    return ganho, proximo


def _bonus_da_trilha(db: Session, *, usuario_id: int, trilha: Trilha) -> int:
    """O bônus de quem acabou de fechar o último passo. Uma vez só por trilha."""
    concluidos = progresso.concluidos_por_trilha(db, usuario_id=usuario_id, trilha_ids=[trilha.id])
    if concluidos.get(trilha.id, 0) < len(trilha.modulos):
        return 0
    ja_pago = db.scalar(
        select(XPEvento.id).where(
            XPEvento.usuario_id == usuario_id,
            XPEvento.origem == OrigemXP.trilha,
            XPEvento.referencia_id == trilha.id,
        )
    )
    if ja_pago is not None:
        return 0
    xp.registrar_xp(
        db,
        usuario_id=usuario_id,
        valor=XP_POR_TRILHA,
        origem=OrigemXP.trilha,
        referencia_id=trilha.id,
    )
    return XP_POR_TRILHA


def acertadas(db: Session, *, usuario_id: int, atividade_ids: list[int]) -> set[int]:
    """Quais destas atividades o aluno já acertou. Uma consulta para a trilha inteira."""
    if not atividade_ids:
        return set()
    return set(
        db.scalars(
            select(RespostaUsuario.atividade_id)
            .where(
                RespostaUsuario.usuario_id == usuario_id,
                RespostaUsuario.atividade_id.in_(atividade_ids),
                RespostaUsuario.correta.is_(True),
            )
            .distinct()
        )
    )


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
