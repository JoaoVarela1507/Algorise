"""Avanço do aluno nas trilhas: estado de cada passo e desbloqueio sequencial.

A regra que manda aqui é uma só: **quem decide o que está liberado é o
servidor**. O caminho de bolinhas da tela 26 mostra cadeado, mas isso é
decoração — um aluno curioso chama `GET /trilhas/x/passos/7` direto e precisa
receber 403, não o conteúdo.

O estado de um passo sai de três coisas: o que está gravado em
`progresso_usuario`, a ordem dele na trilha e o modo de trilha do aluno
(telas 10 a 13):

- **guiada**: passo 1 nasce liberado; o passo N abre quando o N-1 fecha;
- **livre**: tudo liberado, na ordem que o aluno quiser;
- **mista**: segue a ordem nas trilhas do período do aluno (o que a faculdade
  dele pede agora) e é livre nas demais. Sem período informado, não há "ordem
  da faculdade" para seguir, e vale a ordem em tudo, como na guiada.

Trocar de modo não grava nada: o estado é calculado a cada leitura, então o que
foi concluído continua concluído, e só muda o que está aberto daqui em diante.
Um passo fechado fora de ordem no modo livre segue fechado ao voltar para a
guiada, e o próximo depois dele abre normalmente.
"""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Modulo, ProgressoUsuario, StatusProgresso, TipoTrilha, Trilha, Usuario


class PassoBloqueado(Exception):
    """O aluno pediu um passo que ainda não liberou."""


def segue_ordem(trilha: Trilha, usuario: Usuario | None) -> bool:
    """Se, para este aluno, os passos desta trilha abrem um depois do outro.

    Visitante segue a ordem: é o caminho com cadeados que a tela mostra para
    quem ainda não entrou.
    """
    if usuario is None or usuario.tipo_trilha is TipoTrilha.guiada:
        return True
    if usuario.tipo_trilha is TipoTrilha.livre:
        return False
    # Mista.
    return usuario.periodo is None or trilha.periodo == usuario.periodo


def estados_dos_passos(
    db: Session, *, usuario: Usuario | None, trilha: Trilha
) -> dict[int, StatusProgresso]:
    """Estado de cada módulo da trilha, por id.

    Sem aluno (catálogo público), devolve o primeiro passo liberado e o resto
    bloqueado — é o que a tela mostra para quem ainda não entrou.
    """
    concluidos = _modulos_concluidos(
        db, usuario_id=usuario.id if usuario else None, trilha_id=trilha.id
    )
    em_ordem = segue_ordem(trilha, usuario)

    estados: dict[int, StatusProgresso] = {}
    liberado = True  # o primeiro passo nasce aberto

    for modulo in sorted(trilha.modulos, key=lambda m: m.ordem):
        if modulo.id in concluidos:
            estados[modulo.id] = StatusProgresso.concluido
            liberado = True
            continue

        estados[modulo.id] = StatusProgresso.em_andamento if liberado else StatusProgresso.bloqueado
        # Na ordem, o próximo só abre depois que este fechar.
        liberado = not em_ordem

    return estados


def conteudo_do_passo(
    db: Session, *, usuario: Usuario | None, trilha: Trilha, ordem: int
) -> Modulo:
    """O passo pedido, se ele estiver liberado. Levanta `PassoBloqueado` se não.

    A checagem é a mesma de `estados_dos_passos`: uma regra só, para a tela e a
    API nunca discordarem sobre o que está aberto.
    """
    modulo = next((m for m in trilha.modulos if m.ordem == ordem), None)
    if modulo is None:
        raise LookupError(ordem)

    estado = estados_dos_passos(db, usuario=usuario, trilha=trilha)[modulo.id]
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


def esta_concluido(db: Session, *, usuario_id: int, modulo_id: int) -> bool:
    """Se o aluno já fechou este passo. Usado para não pagar o bônus duas vezes."""
    registro = db.execute(
        select(ProgressoUsuario.status).where(
            ProgressoUsuario.usuario_id == usuario_id,
            ProgressoUsuario.modulo_id == modulo_id,
        )
    ).scalar_one_or_none()
    return registro is StatusProgresso.concluido


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
