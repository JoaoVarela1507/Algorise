"""API administrativa: trilhas, passos, atividades e métricas (#41).

Restrita a autor de conteúdo e admin (as métricas, só admin). A interface é o
próprio `/docs` por enquanto; a tela fica para depois.
"""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import exigir_papel
from app.core.database import get_db
from app.core.erros import ErroDeNegocio
from app.models import Atividade, Modulo, PapelUsuario, Parceiro, StatusProgresso, Trilha, Usuario
from app.schemas.admin import (
    AtividadeAdmin,
    AtividadeCriacao,
    AtividadeEdicao,
    MetricasTrilha,
    ParceiroAdmin,
    ParceiroCriacao,
    PassoAdmin,
    PassoCriacao,
    PassoEdicao,
    Publicacao,
    TrilhaAdmin,
    TrilhaCriacao,
    TrilhaEdicao,
    TrilhaImportada,
)
from app.schemas.trilha import ModuloDetalhe, PassoDetalhe
from app.services import admin as servico

AUTOR = exigir_papel(PapelUsuario.autor, PapelUsuario.admin)
ADMIN = exigir_papel(PapelUsuario.admin)

router = APIRouter(prefix="/admin", tags=["admin"])


# --- trilhas ------------------------------------------------------------------------------


@router.get("/trilhas", response_model=list[TrilhaAdmin], summary="Todas as trilhas, com gabarito")
def admin_listar_trilhas(
    _: Usuario = Depends(AUTOR), db: Session = Depends(get_db)
) -> list[Trilha]:
    return servico.listar(db)


@router.post(
    "/trilhas",
    response_model=TrilhaAdmin,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma trilha em rascunho",
)
def admin_criar_trilha(
    dados: TrilhaCriacao, _: Usuario = Depends(AUTOR), db: Session = Depends(get_db)
) -> Trilha:
    try:
        return servico.criar_trilha(db, dados)
    except servico.ParceiroNaoEncontrado as erro:
        raise _nao_encontrado("parceiro", dados.parceiro_id or 0) from erro
    except servico.SlugEmUso as erro:
        raise ErroDeNegocio(
            status_code=status.HTTP_409_CONFLICT,
            code="slug_em_uso",
            message="Já existe uma trilha com esse slug",
            details={"slug": dados.slug},
        ) from erro


@router.patch("/trilhas/{trilha_id}", response_model=TrilhaAdmin, summary="Edita uma trilha")
def admin_editar_trilha(
    trilha_id: int, dados: TrilhaEdicao, _: Usuario = Depends(AUTOR), db: Session = Depends(get_db)
) -> Trilha:
    try:
        return servico.editar_trilha(db, _trilha(db, trilha_id), dados)
    except servico.ParceiroNaoEncontrado as erro:
        raise _nao_encontrado("parceiro", dados.parceiro_id or 0) from erro


@router.delete(
    "/trilhas/{trilha_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Apaga uma trilha sem progresso de aluno",
    description="Com progresso, 409: despublique em vez de apagar.",
)
def admin_apagar_trilha(
    trilha_id: int, _: Usuario = Depends(AUTOR), db: Session = Depends(get_db)
) -> Response:
    try:
        servico.apagar_trilha(db, _trilha(db, trilha_id))
    except servico.ConteudoComProgresso as erro:
        raise _com_progresso() from erro
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/trilhas/{trilha_id}/publicar",
    response_model=TrilhaAdmin,
    summary="Publica ou despublica a trilha",
    description="Publicar confere o gabarito de cada atividade; com problema, 422 com a lista.",
)
def admin_publicar_trilha(
    trilha_id: int, dados: Publicacao, _: Usuario = Depends(AUTOR), db: Session = Depends(get_db)
) -> Trilha:
    try:
        return servico.publicar(db, _trilha(db, trilha_id), dados.publicada)
    except servico.ConteudoInvalido as erro:
        raise _invalido(erro) from erro


@router.post(
    "/trilhas/importar",
    response_model=TrilhaAdmin,
    summary="Importa uma trilha inteira em JSON",
    description=(
        "Cria ou atualiza pelo slug, com passos e atividades pela posição. Passo que "
        "sobra e tem progresso recusa a importação (409)."
    ),
)
def admin_importar_trilha(
    dados: TrilhaImportada, _: Usuario = Depends(AUTOR), db: Session = Depends(get_db)
) -> Trilha:
    try:
        return servico.importar(db, dados)
    except servico.ConteudoComProgresso as erro:
        raise _com_progresso() from erro
    except servico.ConteudoInvalido as erro:
        raise _invalido(erro) from erro


# --- passos -------------------------------------------------------------------------------


@router.post(
    "/trilhas/{trilha_id}/passos",
    response_model=PassoAdmin,
    status_code=status.HTTP_201_CREATED,
    summary="Acrescenta um passo à trilha",
    description="Sem `ordem`, no fim; com ela, os passos dali em diante descem uma posição.",
)
def admin_criar_passo(
    trilha_id: int, dados: PassoCriacao, _: Usuario = Depends(AUTOR), db: Session = Depends(get_db)
) -> Modulo:
    return servico.criar_passo(db, _trilha(db, trilha_id), dados)


@router.patch(
    "/trilhas/{trilha_id}/passos/{passo_id}",
    response_model=PassoAdmin,
    summary="Edita ou move um passo",
)
def admin_editar_passo(
    trilha_id: int,
    passo_id: int,
    dados: PassoEdicao,
    _: Usuario = Depends(AUTOR),
    db: Session = Depends(get_db),
) -> Modulo:
    return servico.editar_passo(db, _passo(db, trilha_id, passo_id), dados)


@router.delete(
    "/trilhas/{trilha_id}/passos/{passo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Apaga um passo sem progresso de aluno",
)
def admin_apagar_passo(
    trilha_id: int, passo_id: int, _: Usuario = Depends(AUTOR), db: Session = Depends(get_db)
) -> Response:
    try:
        servico.apagar_passo(db, _passo(db, trilha_id, passo_id))
    except servico.ConteudoComProgresso as erro:
        raise _com_progresso() from erro
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/passos/{passo_id}/previa",
    response_model=PassoDetalhe,
    summary="O passo como o aluno vê",
    description="Sem gabarito, liberado, mesmo em trilha que ainda não foi publicada.",
)
def admin_previa_do_passo(
    passo_id: int, _: Usuario = Depends(AUTOR), db: Session = Depends(get_db)
) -> PassoDetalhe:
    passo = db.get(Modulo, passo_id)
    if passo is None:
        raise _nao_encontrado("passo", passo_id)
    ordens = sorted(m.ordem for m in passo.trilha.modulos)
    return PassoDetalhe(
        **ModuloDetalhe.model_validate(passo).model_dump(
            exclude={"status", "concluido", "bloqueado"}
        ),
        status=StatusProgresso.em_andamento,
        concluido=False,
        bloqueado=False,
        trilha_slug=passo.trilha.slug,
        trilha_nome=passo.trilha.nome,
        total_passos=len(ordens),
        proximo=passo.ordem + 1 if passo.ordem < max(ordens) else None,
    )


# --- atividades ---------------------------------------------------------------------------


@router.post(
    "/atividades",
    response_model=AtividadeAdmin,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma atividade num passo",
)
def admin_criar_atividade(
    dados: AtividadeCriacao, _: Usuario = Depends(AUTOR), db: Session = Depends(get_db)
) -> Atividade:
    passo = db.get(Modulo, dados.passo_id)
    if passo is None:
        raise _nao_encontrado("passo", dados.passo_id)
    try:
        return servico.criar_atividade(db, passo, dados)
    except servico.ConteudoInvalido as erro:
        raise _invalido(erro) from erro


@router.patch(
    "/atividades/{atividade_id}", response_model=AtividadeAdmin, summary="Edita uma atividade"
)
def admin_editar_atividade(
    atividade_id: int,
    dados: AtividadeEdicao,
    _: Usuario = Depends(AUTOR),
    db: Session = Depends(get_db),
) -> Atividade:
    try:
        return servico.editar_atividade(db, _atividade(db, atividade_id), dados)
    except servico.ConteudoInvalido as erro:
        raise _invalido(erro) from erro


@router.delete(
    "/atividades/{atividade_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Apaga uma atividade que ninguém respondeu",
)
def admin_apagar_atividade(
    atividade_id: int, _: Usuario = Depends(AUTOR), db: Session = Depends(get_db)
) -> Response:
    try:
        servico.apagar_atividade(db, _atividade(db, atividade_id))
    except servico.ConteudoComProgresso as erro:
        raise _com_progresso() from erro
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- parceiros ----------------------------------------------------------------------------


@router.get("/parceiros", response_model=list[ParceiroAdmin], summary="Parceiros que certificam")
def admin_listar_parceiros(
    _: Usuario = Depends(AUTOR), db: Session = Depends(get_db)
) -> list[Parceiro]:
    return servico.listar_parceiros(db)


@router.post(
    "/parceiros",
    response_model=ParceiroAdmin,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um parceiro",
    description="A trilha com `parceiro_id` passa a emitir certificado. Só admin.",
)
def admin_criar_parceiro(
    dados: ParceiroCriacao, _: Usuario = Depends(ADMIN), db: Session = Depends(get_db)
) -> Parceiro:
    return servico.criar_parceiro(db, dados)


# --- métricas -----------------------------------------------------------------------------


@router.get(
    "/metricas",
    response_model=list[MetricasTrilha],
    summary="Desempenho por trilha e por atividade",
    description=(
        "Conclusão por trilha; por atividade, tentativas, acerto, abandono (tentou e nunca "
        "acertou) e, no terminal, as respostas erradas mais comuns. Só admin."
    ),
)
def admin_metricas(
    _: Usuario = Depends(ADMIN), db: Session = Depends(get_db)
) -> list[MetricasTrilha]:
    return servico.metricas(db)


# --- apoio --------------------------------------------------------------------------------


def _trilha(db: Session, trilha_id: int) -> Trilha:
    trilha = db.get(Trilha, trilha_id)
    if trilha is None:
        raise _nao_encontrado("trilha", trilha_id)
    return trilha


def _passo(db: Session, trilha_id: int, passo_id: int) -> Modulo:
    passo = db.get(Modulo, passo_id)
    if passo is None or passo.trilha_id != trilha_id:
        raise _nao_encontrado("passo", passo_id)
    return passo


def _atividade(db: Session, atividade_id: int) -> Atividade:
    atividade = db.get(Atividade, atividade_id)
    if atividade is None:
        raise _nao_encontrado("atividade", atividade_id)
    return atividade


_NAO_ENCONTRADO = {
    "parceiro": ("parceiro_nao_encontrado", "Parceiro não encontrado"),
    "trilha": ("trilha_nao_encontrada", "Trilha não encontrada"),
    "passo": ("passo_nao_encontrado", "Passo não encontrado"),
    "atividade": ("atividade_nao_encontrada", "Atividade não encontrada"),
}


def _nao_encontrado(o_que: str, identificador: int) -> ErroDeNegocio:
    codigo, mensagem = _NAO_ENCONTRADO[o_que]
    return ErroDeNegocio(
        status_code=status.HTTP_404_NOT_FOUND,
        code=codigo,
        message=mensagem,
        details={"id": identificador},
    )


def _com_progresso() -> ErroDeNegocio:
    return ErroDeNegocio(
        status_code=status.HTTP_409_CONFLICT,
        code="conteudo_com_progresso",
        message="Há alunos com progresso ou respostas aqui. Despublique em vez de apagar.",
    )


def _invalido(erro: Exception) -> ErroDeNegocio:
    problemas = getattr(erro, "problemas", [])
    return ErroDeNegocio(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="conteudo_invalido",
        message="O conteúdo tem problemas que impedem a publicação",
        details={"problemas": [p.model_dump(exclude_none=True) for p in problemas]},
    )
