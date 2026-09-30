from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core import cache
from app.core.config import settings
from app.core.database import get_db
from app.core.erros import ErroDeNegocio
from app.schemas.pagina import Pagina, PaginacaoAtual
from app.schemas.trilha import Trilha, TrilhaDetalhe
from app.services import trilhas as servico

router = APIRouter(prefix="/trilhas", tags=["trilhas"])


@router.get(
    "",
    response_model=Pagina[Trilha],
    summary="Catálogo de trilhas",
    description=(
        "Trilhas publicadas, paginadas. Aceita `ordenar_por` em `periodo`, `nome` ou `disciplina`."
    ),
)
def listar_trilhas(
    paginacao: PaginacaoAtual,
    db: Session = Depends(get_db),
    busca: str | None = Query(default=None, description="Filtra por nome ou disciplina"),
    periodo: int | None = Query(default=None, ge=1, le=8, description="Período letivo"),
) -> Pagina[Trilha]:
    # O catálogo é igual para todos os alunos (telas 24 e 25), então cabe em cache
    # compartilhado. A chave inclui filtros e página: cada combinação é um
    # conteúdo diferente.
    nome = servico.chave_do_catalogo(busca=busca, periodo=periodo, pagina=paginacao)

    em_cache = cache.obter_json(nome)
    if em_cache is not None:
        return Pagina[Trilha].model_validate(em_cache)

    resultados, total = servico.listar_trilhas(db, busca=busca, periodo=periodo, pagina=paginacao)
    pagina = Pagina[Trilha].montar(
        [
            Trilha.model_validate(trilha).model_copy(update={"total_modulos": modulos})
            for trilha, modulos in resultados
        ],
        pagina=paginacao.pagina,
        tamanho_pagina=paginacao.tamanho_pagina,
        total=total,
    )

    cache.definir_json(nome, pagina.model_dump(mode="json"), settings.cache_ttl_trilhas)
    return pagina


@router.get(
    "/{slug}",
    response_model=TrilhaDetalhe,
    summary="Trilha com módulos e atividades",
)
def obter_trilha(slug: str, db: Session = Depends(get_db)) -> TrilhaDetalhe:
    trilha = servico.obter_trilha(db, slug)
    if trilha is None:
        raise ErroDeNegocio(
            status_code=status.HTTP_404_NOT_FOUND,
            code="trilha_nao_encontrada",
            message="Trilha não encontrada",
            details={"slug": slug},
        )

    detalhe = TrilhaDetalhe.model_validate(trilha)
    # O primeiro passo nasce liberado; o resto depende do progresso do aluno,
    # que entra junto com a autenticação (#10) e o progresso (#30).
    for indice, modulo in enumerate(detalhe.modulos):
        modulo.bloqueado = indice > 0
    return detalhe.model_copy(update={"total_modulos": len(detalhe.modulos)})
