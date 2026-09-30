"""Consultas de trilha, separadas das rotas para poderem ser testadas sozinhas."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core import cache
from app.models import Modulo, Trilha
from app.schemas.pagina import Paginacao

# Prefixo próprio para o catálogo poder ser invalidado inteiro de uma vez, sem
# precisar saber que combinações de busca e período alguém consultou.
PREFIXO_CATALOGO = cache.chave("trilhas", "catalogo")


# Por onde a listagem aceita ordenar. Nome público -> coluna, para o cliente
# nunca escolher uma coluna que não está aqui (ver `Paginacao.campo_ordenado`).
ORDENACOES = {
    "periodo": Trilha.periodo,
    "nome": Trilha.nome,
    "disciplina": Trilha.disciplina,
}
ORDENACAO_PADRAO = "periodo"


def chave_do_catalogo(*, busca: str | None, periodo: int | None, pagina: "Paginacao") -> str:
    """Chave de cache da listagem.

    A busca entra normalizada para "Python" e "python " não virarem duas
    entradas com o mesmo conteúdo. A página faz parte da chave: duas páginas
    diferentes são dois conteúdos diferentes.
    """
    termo = (busca or "").strip().lower()
    ordem = f"{pagina.ordenar_por or ORDENACAO_PADRAO}:{'desc' if pagina.decrescente else 'asc'}"
    return (
        f"{PREFIXO_CATALOGO}:{termo}:{periodo or 'todos'}"
        f":{pagina.pagina}:{pagina.tamanho_pagina}:{ordem}"
    )


def invalidar_catalogo() -> int:
    """Descarta o catálogo em cache. Para quem publica ou edita trilha chamar."""
    return cache.invalidar_prefixo(f"{PREFIXO_CATALOGO}:")


def listar_trilhas(
    db: Session,
    *,
    busca: str | None = None,
    periodo: int | None = None,
    apenas_publicadas: bool = True,
    pagina: "Paginacao | None" = None,
) -> tuple[list[tuple[Trilha, int]], int]:
    """Uma página do catálogo e o total de trilhas que o filtro encontrou.

    A contagem de módulos vem por subquery em vez de carregar os módulos: a tela
    24 mostra "3/10" para dezenas de cards de uma vez. O total, por sua vez, é
    contado sem a paginação — é ele que diz quantas páginas existem.
    """
    total_modulos = (
        select(func.count(Modulo.id))
        .where(Modulo.trilha_id == Trilha.id)
        .correlate(Trilha)
        .scalar_subquery()
    )

    consulta = select(Trilha, total_modulos)

    if apenas_publicadas:
        consulta = consulta.where(Trilha.publicada.is_(True))
    if periodo is not None:
        consulta = consulta.where(Trilha.periodo == periodo)
    if busca:
        termo = f"%{busca.strip()}%"
        consulta = consulta.where(Trilha.nome.ilike(termo) | Trilha.disciplina.ilike(termo))

    # Conta antes de paginar, reaproveitando os mesmos filtros.
    total = db.execute(
        select(func.count()).select_from(consulta.order_by(None).subquery())
    ).scalar_one()

    if pagina is None:
        consulta = consulta.order_by(Trilha.periodo, Trilha.nome)
        return [(trilha, modulos) for trilha, modulos in db.execute(consulta).all()], total

    campo = pagina.campo_ordenado(ORDENACOES, ORDENACAO_PADRAO)
    ordem = campo.desc() if pagina.decrescente else campo.asc()
    # O `id` no fim desempata: sem ele, duas trilhas do mesmo período podem
    # trocar de lugar entre uma página e outra.
    consulta = (
        consulta.order_by(ordem, Trilha.id).offset(pagina.deslocamento).limit(pagina.tamanho_pagina)
    )

    return [(trilha, modulos) for trilha, modulos in db.execute(consulta).all()], total


def obter_trilha(db: Session, slug: str) -> Trilha | None:
    """Trilha com módulos e atividades, em uma consulta só."""
    consulta = (
        select(Trilha)
        .where(Trilha.slug == slug)
        .options(selectinload(Trilha.modulos).selectinload(Modulo.atividades))
    )
    return db.execute(consulta).scalar_one_or_none()
