"""Avanço do aluno nas trilhas: estado de cada passo e desbloqueio sequencial.

A regra que manda aqui é uma só: **quem decide o que está liberado é o
servidor**. O caminho de bolinhas da tela 26 mostra cadeado, mas isso é
decoração — um aluno curioso chama `GET /trilhas/x/passos/7` direto e precisa
receber 403, não o conteúdo.

O estado de um passo sai de duas coisas: o que está gravado em
`progresso_usuario` e a ordem dele na trilha. Passo 1 nasce liberado; o passo N
abre quando o N-1 fecha.
"""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Modulo, ProgressoUsuario, StatusProgresso, Trilha


class PassoBloqueado(Exception):
    """O aluno pediu um passo que ainda não liberou."""


def estados_dos_passos(
    db: Session, *, usuario_id: int | None, trilha: Trilha
) -> dict[int, StatusProgresso]:
    """Estado de cada módulo da trilha, por id.

    Sem aluno (catálogo público), devolve o primeiro passo liberado e o resto
    bloqueado — é o que a tela mostra para quem ainda não entrou.
    """
    concluidos = _modulos_concluidos(db, usuario_id=usuario_id, trilha_id=trilha.id)

    estados: dict[int, StatusProgresso] = {}
    liberado = True  # o primeiro passo nasce aberto

    for modulo in sorted(trilha.modulos, key=lambda m: m.ordem):
        if modulo.id in concluidos:
            estados[modulo.id] = StatusProgresso.concluido
            liberado = True
            continue

        estados[modulo.id] = StatusProgresso.em_andamento if liberado else StatusProgresso.bloqueado
        # O próximo só abre depois que este fechar.
        liberado = False

    return estados


def conteudo_do_passo(db: Session, *, usuario_id: int | None, trilha: Trilha, ordem: int) -> Modulo:
    """O passo pedido, se ele estiver liberado. Levanta `PassoBloqueado` se não.

    A checagem é a mesma de `estados_dos_passos`: uma regra só, para a tela e a
    API nunca discordarem sobre o que está aberto.
    """
    modulo = next((m for m in trilha.modulos if m.ordem == ordem), None)
    if modulo is None:
        raise LookupError(ordem)

    estado = estados_dos_passos(db, usuario_id=usuario_id, trilha=trilha)[modulo.id]
    if estado is StatusProgresso.bloqueado:
        raise PassoBloqueado(ordem)

    return modulo


def iniciar_trilha(db: Session, *, usuario_id: int, trilha: Trilha) -> ProgressoUsuario | None:
    """Marca o primeiro passo como em andamento e devolve o registro.

    Idempotente de propósito: quem já começou continua de onde parou. Chamar de
    novo não apaga nada — o botão "iniciar" da tela 24 fica visível mesmo depois
    de a trilha ter começado.
    """
    if not trilha.modulos:
        return None

    primeiro = min(trilha.modulos, key=lambda m: m.ordem)

    ja_comecou = db.execute(
        select(ProgressoUsuario)
        .where(
            ProgressoUsuario.usuario_id == usuario_id,
            ProgressoUsuario.trilha_id == trilha.id,
        )
        .limit(1)
    ).scalar_one_or_none()

    if ja_comecou is not None:
        return ja_comecou

    progresso = ProgressoUsuario(
        usuario_id=usuario_id,
        trilha_id=trilha.id,
        modulo_id=primeiro.id,
        status=StatusProgresso.em_andamento,
    )
    db.add(progresso)
    db.commit()
    return progresso


def concluir_passo(db: Session, *, usuario_id: int, trilha: Trilha, modulo: Modulo) -> None:
    """Fecha o passo do aluno. Chamado pela submissão de atividade (#30)."""
    registro = db.execute(
        select(ProgressoUsuario).where(
            ProgressoUsuario.usuario_id == usuario_id,
            ProgressoUsuario.modulo_id == modulo.id,
        )
    ).scalar_one_or_none()

    if registro is None:
        registro = ProgressoUsuario(usuario_id=usuario_id, trilha_id=trilha.id, modulo_id=modulo.id)
        db.add(registro)

    registro.status = StatusProgresso.concluido
    registro.concluido_em = registro.concluido_em or datetime.now(UTC)
    db.commit()


def concluidos_por_trilha(db: Session, *, usuario_id: int, trilha_ids: list[int]) -> dict[int, int]:
    """Quantos passos o aluno fechou em cada trilha, para o "3/10" dos cards.

    Uma consulta para a página inteira, em vez de uma por card.
    """
    if not trilha_ids:
        return {}

    linhas = db.execute(
        select(ProgressoUsuario.trilha_id, func.count(ProgressoUsuario.id))
        .where(
            ProgressoUsuario.usuario_id == usuario_id,
            ProgressoUsuario.trilha_id.in_(trilha_ids),
            ProgressoUsuario.status == StatusProgresso.concluido,
        )
        .group_by(ProgressoUsuario.trilha_id)
    ).all()

    return {trilha_id: total for trilha_id, total in linhas}


def _modulos_concluidos(db: Session, *, usuario_id: int | None, trilha_id: int) -> set[int]:
    if usuario_id is None:
        return set()

    linhas = db.execute(
        select(ProgressoUsuario.modulo_id).where(
            ProgressoUsuario.usuario_id == usuario_id,
            ProgressoUsuario.trilha_id == trilha_id,
            ProgressoUsuario.status == StatusProgresso.concluido,
        )
    ).scalars()

    return set(linhas)
