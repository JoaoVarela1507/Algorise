"""Consultas de trilha, separadas das rotas para poderem ser testadas sozinhas."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core import cache
from app.models import Modulo, NivelExperiencia, Trilha, Usuario
from app.schemas.pagina import Paginacao
from app.services import progresso

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


def chave_do_catalogo(
    *,
    busca: str | None,
    periodo: int | None,
    categoria: str | None,
    pagina: "Paginacao",
) -> str:
    """Chave de cache da listagem.

    A busca e a categoria entram normalizadas para "Python" e "python " não
    virarem duas entradas com o mesmo conteúdo. A página faz parte da chave:
    duas páginas diferentes são dois conteúdos diferentes.

    O aluno **não** entra na chave, de propósito: o cache guarda o catálogo, que
    é igual para todo mundo, e o progresso de cada um é sobreposto depois (ver
    `app/api/v1/trilhas.py`). Misturar os dois aqui criaria uma cópia do
    catálogo por aluno.
    """
    termo = (busca or "").strip().lower()
    filtro_categoria = (categoria or "").strip().lower() or "todas"
    ordem = f"{pagina.ordenar_por or ORDENACAO_PADRAO}:{'desc' if pagina.decrescente else 'asc'}"
    return (
        f"{PREFIXO_CATALOGO}:{termo}:{periodo or 'todos'}:{filtro_categoria}"
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
    categoria: str | None = None,
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
    if categoria:
        # Comparação sem diferenciar maiúsculas: a categoria vem de um filtro da
        # tela, não de um id.
        consulta = consulta.where(func.lower(Trilha.categoria) == categoria.strip().lower())
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


# Quantas trilhas a tela 24 sugere de uma vez.
LIMITE_DE_RECOMENDACOES = 6

MOTIVO_PERIODO = "Combina com o seu período"
MOTIVO_PROXIMO = "Vem logo depois do seu período"
MOTIVO_NIVEL = "Boa para quem está começando"
MOTIVO_GERAL = "Conhecimentos gerais"


def recomendar_trilhas(
    db: Session, usuario: "Usuario", *, limite: int = LIMITE_DE_RECOMENDACOES
) -> list[tuple[Trilha, int, str]]:
    """Trilhas sugeridas para o aluno, cada uma com o motivo de ter aparecido.

    A regra usa o que o onboarding coletou: período e nível. A recomendação a
    partir da ementa em PDF depende da #38 — quando ela existir, entra aqui sem
    mudar o contrato, porque o motivo já viaja junto.

    Trilha concluída sai da lista: sugerir o que o aluno já terminou é ruído.
    """
    trilhas, _ = listar_trilhas(db, apenas_publicadas=True)
    if not trilhas:
        return []

    concluidos = progresso.concluidos_por_trilha(
        db, usuario_id=usuario.id, trilha_ids=[trilha.id for trilha, _ in trilhas]
    )

    candidatas: list[tuple[Trilha, int, str]] = []
    for trilha, total_modulos in trilhas:
        feitos = concluidos.get(trilha.id, 0)
        if total_modulos and feitos >= total_modulos:
            continue
        candidatas.append((trilha, total_modulos, _motivo(trilha, usuario)))

    # Quem casa com o período do aluno aparece primeiro; depois o que vem logo
    # a seguir; o resto fecha a lista.
    prioridade = {MOTIVO_PERIODO: 0, MOTIVO_PROXIMO: 1, MOTIVO_NIVEL: 2, MOTIVO_GERAL: 3}
    candidatas.sort(key=lambda item: (prioridade[item[2]], item[0].periodo or 99, item[0].nome))

    return candidatas[:limite]


def _motivo(trilha: Trilha, usuario: "Usuario") -> str:
    if usuario.periodo is not None and trilha.periodo == usuario.periodo:
        return MOTIVO_PERIODO
    if usuario.periodo is not None and trilha.periodo == usuario.periodo + 1:
        return MOTIVO_PROXIMO
    if usuario.nivel_experiencia is NivelExperiencia.baixo and (trilha.periodo or 9) <= 2:
        return MOTIVO_NIVEL
    return MOTIVO_GERAL
