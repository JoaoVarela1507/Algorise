"""Catálogo, caminho da trilha e conteúdo de cada passo (telas 24, 25 e 26)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import Field
from sqlalchemy.orm import Session

from app.api.deps import UsuarioAtual, UsuarioOpcional
from app.core import cache
from app.core.config import settings
from app.core.database import get_db
from app.core.erros import ErroDeNegocio
from app.models import StatusProgresso, Usuario
from app.models import Trilha as TrilhaModelo
from app.schemas.pagina import Pagina, PaginacaoAtual
from app.schemas.trilha import (
    ModuloDetalhe,
    PassoDetalhe,
    Trilha,
    TrilhaDetalhe,
    TrilhaRecomendada,
)
from app.services import progresso as servico_progresso
from app.services import trilhas as servico

router = APIRouter(prefix="/trilhas", tags=["trilhas"])

# 1 a 8, como os períodos do curso.
PeriodoLetivo = Annotated[int, Field(ge=1, le=8)]


@router.get(
    "",
    response_model=Pagina[Trilha],
    summary="Catálogo de trilhas",
    description=(
        "Trilhas publicadas, paginadas. Com token, cada card vem com o progresso "
        "do aluno. Aceita `ordenar_por` em `periodo`, `nome` ou `disciplina`."
    ),
)
def listar_trilhas(
    paginacao: PaginacaoAtual,
    usuario: UsuarioOpcional,
    db: Session = Depends(get_db),
    busca: str | None = Query(default=None, description="Filtra por nome ou disciplina"),
    # A restrição vai no item, e não na lista: `ge` aplicado a `list[int]`
    # tentaria comparar a lista inteira com 1 e estoura.
    periodo: list[PeriodoLetivo] | None = Query(
        default=None, description="Período letivo; pode repetir para filtrar vários"
    ),
    categoria: str | None = Query(default=None, description="Categoria do card (tela 24)"),
) -> Pagina[Trilha]:
    # O catálogo é igual para todos os alunos, então cabe em cache compartilhado.
    # O progresso, que é de cada um, entra depois — misturar os dois na chave
    # criaria uma cópia do catálogo por aluno.
    nome = servico.chave_do_catalogo(
        busca=busca, periodo=periodo, categoria=categoria, pagina=paginacao
    )

    em_cache = cache.obter_json(nome)
    if em_cache is not None:
        pagina = Pagina[Trilha].model_validate(em_cache)
        return _com_progresso(db, pagina, usuario)

    resultados, total = servico.listar_trilhas(
        db, busca=busca, periodo=periodo, categoria=categoria, pagina=paginacao
    )
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
    return _com_progresso(db, pagina, usuario)


@router.get(
    "/recomendadas",
    response_model=list[TrilhaRecomendada],
    summary="Trilhas sugeridas para o aluno",
)
def listar_recomendadas(
    usuario: UsuarioAtual, db: Session = Depends(get_db)
) -> list[TrilhaRecomendada]:
    """Sugestões conforme o período e o nível informados no onboarding.

    Fica antes de `/{slug}` de propósito: declarada depois, a rota de detalhe
    engoliria "recomendadas" como se fosse um slug.
    """
    sugeridas = servico.recomendar_trilhas(db, usuario)
    concluidos = servico_progresso.concluidos_por_trilha(
        db, usuario_id=usuario.id, trilha_ids=[trilha.id for trilha, _, _ in sugeridas]
    )

    return [
        _recomendada(trilha, total_modulos, concluidos.get(trilha.id, 0), motivo)
        for trilha, total_modulos, motivo in sugeridas
    ]


@router.get("/{slug}", response_model=TrilhaDetalhe, summary="Trilha com os passos e seus estados")
def obter_trilha(
    slug: str, usuario: UsuarioOpcional, db: Session = Depends(get_db)
) -> TrilhaDetalhe:
    trilha = _buscar(db, slug)
    estados = servico_progresso.estados_dos_passos(
        db, usuario_id=usuario.id if usuario else None, trilha=trilha
    )

    detalhe = TrilhaDetalhe.model_validate(trilha)
    detalhe.modulos = [_com_estado(modulo, estados[modulo.id]) for modulo in detalhe.modulos]

    return detalhe.model_copy(
        update={
            "total_modulos": len(detalhe.modulos),
            "progresso": sum(1 for m in detalhe.modulos if m.concluido),
        }
    )


@router.get(
    "/{slug}/passos/{ordem}",
    response_model=PassoDetalhe,
    summary="Conteúdo de um passo",
    description="Recusa com 403 o passo que o aluno ainda não desbloqueou.",
)
def obter_passo(
    slug: str, ordem: int, usuario: UsuarioOpcional, db: Session = Depends(get_db)
) -> PassoDetalhe:
    trilha = _buscar(db, slug)
    usuario_id = usuario.id if usuario else None

    try:
        modulo = servico_progresso.conteudo_do_passo(
            db, usuario_id=usuario_id, trilha=trilha, ordem=ordem
        )
    except LookupError as erro:
        raise ErroDeNegocio(
            status_code=status.HTTP_404_NOT_FOUND,
            code="passo_nao_encontrado",
            message="Esse passo não existe nesta trilha",
            details={"trilha": slug, "ordem": ordem},
        ) from erro
    except servico_progresso.PassoBloqueado as erro:
        raise ErroDeNegocio(
            status_code=status.HTTP_403_FORBIDDEN,
            code="passo_bloqueado",
            message="Conclua o passo anterior para abrir este",
            details={"trilha": slug, "ordem": ordem},
        ) from erro

    estados = servico_progresso.estados_dos_passos(db, usuario_id=usuario_id, trilha=trilha)
    ordens = sorted(m.ordem for m in trilha.modulos)

    # `model_validate` direto não serve: `PassoDetalhe` pede campos que não
    # existem no módulo (o nome da trilha, o total de passos), e eles precisam
    # entrar na construção, não depois.
    passo = PassoDetalhe(
        **ModuloDetalhe.model_validate(modulo).model_dump(),
        trilha_slug=trilha.slug,
        trilha_nome=trilha.nome,
        total_passos=len(ordens),
        proximo=ordem + 1 if ordem < max(ordens) else None,
    )
    return _com_estado(passo, estados[modulo.id])


@router.post(
    "/{slug}/iniciar",
    response_model=TrilhaDetalhe,
    status_code=status.HTTP_200_OK,
    summary="Começa a trilha para o aluno",
    description="Idempotente: quem já começou continua de onde parou.",
)
def iniciar_trilha(
    slug: str, usuario: UsuarioAtual, db: Session = Depends(get_db)
) -> TrilhaDetalhe:
    trilha = _buscar(db, slug)
    servico_progresso.iniciar_trilha(db, usuario_id=usuario.id, trilha=trilha)

    return obter_trilha(slug, usuario, db)


def _recomendada(
    trilha: TrilhaModelo, total_modulos: int, progresso: int, motivo: str
) -> TrilhaRecomendada:
    dados = Trilha.model_validate(trilha).model_dump()
    dados.update(total_modulos=total_modulos, progresso=progresso)
    return TrilhaRecomendada(**dados, motivo=motivo)


def _buscar(db: Session, slug: str) -> TrilhaModelo:
    trilha = servico.obter_trilha(db, slug)
    if trilha is None or not trilha.publicada:
        # Trilha em rascunho responde como inexistente: quem não pode vê-la não
        # precisa saber que ela existe.
        raise ErroDeNegocio(
            status_code=status.HTTP_404_NOT_FOUND,
            code="trilha_nao_encontrada",
            message="Trilha não encontrada",
            details={"slug": slug},
        )
    return trilha


def _com_progresso(db: Session, pagina: Pagina[Trilha], usuario: Usuario | None) -> Pagina[Trilha]:
    """Sobrepõe o progresso do aluno na página vinda do cache (ou do banco)."""
    if usuario is None or not pagina.itens:
        return pagina

    concluidos = servico_progresso.concluidos_por_trilha(
        db, usuario_id=usuario.id, trilha_ids=[trilha.id for trilha in pagina.itens]
    )
    pagina.itens = [
        trilha.model_copy(update={"progresso": concluidos.get(trilha.id, 0)})
        for trilha in pagina.itens
    ]
    return pagina


def _com_estado[T: ModuloDetalhe](modulo: T, estado: StatusProgresso) -> T:
    """`status` é a verdade; `concluido` e `bloqueado` seguem dele.

    Os dois booleanos existem porque a tela já os consome; mantê-los derivados
    evita a situação de um dizer uma coisa e o outro dizer outra.
    """
    return modulo.model_copy(
        update={
            "status": estado,
            "concluido": estado is StatusProgresso.concluido,
            "bloqueado": estado is StatusProgresso.bloqueado,
        }
    )
