"""Consultas de trilha, separadas das rotas para poderem ser testadas sozinhas."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Modulo, Trilha


def listar_trilhas(
    db: Session,
    *,
    busca: str | None = None,
    periodo: int | None = None,
    apenas_publicadas: bool = True,
) -> list[tuple[Trilha, int]]:
    """Trilhas do catálogo com a contagem de módulos de cada uma.

    A contagem vem por subquery em vez de carregar os módulos: a tela 24 mostra
    "3/10" para dezenas de cards de uma vez.
    """
    total_modulos = (
        select(func.count(Modulo.id))
        .where(Modulo.trilha_id == Trilha.id)
        .correlate(Trilha)
        .scalar_subquery()
    )

    consulta = select(Trilha, total_modulos).order_by(Trilha.periodo, Trilha.nome)

    if apenas_publicadas:
        consulta = consulta.where(Trilha.publicada.is_(True))
    if periodo is not None:
        consulta = consulta.where(Trilha.periodo == periodo)
    if busca:
        termo = f"%{busca.strip()}%"
        consulta = consulta.where(Trilha.nome.ilike(termo) | Trilha.disciplina.ilike(termo))

    return [(trilha, total) for trilha, total in db.execute(consulta).all()]


def obter_trilha(db: Session, slug: str) -> Trilha | None:
    """Trilha com módulos e atividades, em uma consulta só."""
    consulta = (
        select(Trilha)
        .where(Trilha.slug == slug)
        .options(selectinload(Trilha.modulos).selectinload(Modulo.atividades))
    )
    return db.execute(consulta).scalar_one_or_none()
