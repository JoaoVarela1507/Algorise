"""Parte REST do chat: conversas, histórico, busca, grupos e sugestões (#33).

O envio de mensagens, com a resposta em streaming, fica em `chat.py`.
"""

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import UsuarioAtual
from app.core.database import get_db
from app.core.erros import ErroDeNegocio
from app.schemas.conversas import (
    ConversaResumo,
    EdicaoDeConversa,
    EdicaoDeGrupo,
    Grupo,
    Mensagem,
    NovaConversa,
    NovoGrupo,
    Sugestao,
)
from app.schemas.pagina import Pagina, PaginacaoAtual
from app.services import conversas as servico

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "/conversas",
    response_model=ConversaResumo,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma conversa",
    description='O título sai da `primeira_mensagem`, se vier; senão, "Nova conversa".',
)
def criar_conversa(
    dados: NovaConversa, usuario: UsuarioAtual, db: Session = Depends(get_db)
) -> ConversaResumo:
    return ConversaResumo.model_validate(servico.criar(db, usuario, dados))


@router.get(
    "/conversas",
    response_model=Pagina[ConversaResumo],
    summary="Histórico de conversas",
    description=(
        "Da mais recente para a mais antiga. `busca` procura a palavra no título e no "
        "conteúdo das mensagens (full-text em português no PostgreSQL)."
    ),
)
def listar_conversas(
    paginacao: PaginacaoAtual,
    usuario: UsuarioAtual,
    db: Session = Depends(get_db),
    busca: str | None = Query(default=None, max_length=200),
    arquivadas: bool = Query(default=False, description="As arquivadas, em vez das ativas"),
    grupo_id: int | None = Query(default=None, description="Só as de um grupo"),
) -> Pagina[ConversaResumo]:
    itens, total = servico.listar(
        db, usuario, paginacao, busca=busca, arquivadas=arquivadas, grupo_id=grupo_id
    )
    return Pagina[ConversaResumo].montar(
        [ConversaResumo.model_validate(c) for c in itens],
        pagina=paginacao.pagina,
        tamanho_pagina=paginacao.tamanho_pagina,
        total=total,
    )


@router.get(
    "/conversas/{conversa_id}/mensagens",
    response_model=Pagina[Mensagem],
    summary="Mensagens da conversa, na ordem",
)
def listar_mensagens(
    conversa_id: int,
    paginacao: PaginacaoAtual,
    usuario: UsuarioAtual,
    db: Session = Depends(get_db),
) -> Pagina[Mensagem]:
    try:
        itens, total = servico.mensagens(db, usuario, conversa_id, paginacao)
    except servico.NaoEncontrado as erro:
        raise _nao_encontrada("conversa", conversa_id) from erro
    return Pagina[Mensagem].montar(
        [Mensagem.model_validate(m) for m in itens],
        pagina=paginacao.pagina,
        tamanho_pagina=paginacao.tamanho_pagina,
        total=total,
    )


@router.patch(
    "/conversas/{conversa_id}",
    response_model=ConversaResumo,
    summary="Renomeia, arquiva ou põe a conversa num grupo",
)
def editar_conversa(
    conversa_id: int,
    dados: EdicaoDeConversa,
    usuario: UsuarioAtual,
    db: Session = Depends(get_db),
) -> ConversaResumo:
    try:
        return ConversaResumo.model_validate(servico.editar(db, usuario, conversa_id, dados))
    except servico.NaoEncontrado as erro:
        raise _nao_encontrada("conversa", conversa_id) from erro


@router.delete(
    "/conversas/{conversa_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Apaga a conversa e as mensagens",
)
def apagar_conversa(
    conversa_id: int, usuario: UsuarioAtual, db: Session = Depends(get_db)
) -> Response:
    try:
        servico.apagar(db, usuario, conversa_id)
    except servico.NaoEncontrado as erro:
        raise _nao_encontrada("conversa", conversa_id) from erro
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/sugestoes",
    response_model=list[Sugestao],
    summary="Tópicos sugeridos na tela 21",
    description="O passo em que o aluno está e as conversas recentes.",
)
def listar_sugestoes(usuario: UsuarioAtual, db: Session = Depends(get_db)) -> list[Sugestao]:
    return [Sugestao(**item) for item in servico.sugestoes(db, usuario)]


# --- grupos -------------------------------------------------------------------------------


@router.post(
    "/grupos",
    response_model=Grupo,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um grupo temático com as conversas escolhidas",
)
def criar_grupo(dados: NovoGrupo, usuario: UsuarioAtual, db: Session = Depends(get_db)) -> Grupo:
    try:
        return Grupo.model_validate(servico.criar_grupo(db, usuario, dados))
    except servico.NaoEncontrado as erro:
        raise _nao_encontrada("conversa", None) from erro


@router.get("/grupos", response_model=list[Grupo], summary="Grupos do aluno")
def listar_grupos(usuario: UsuarioAtual, db: Session = Depends(get_db)) -> list[Grupo]:
    return [Grupo.model_validate(g) for g in servico.listar_grupos(db, usuario)]


@router.get("/grupos/{grupo_id}", response_model=Grupo, summary="Um grupo, com as conversas")
def obter_grupo(grupo_id: int, usuario: UsuarioAtual, db: Session = Depends(get_db)) -> Grupo:
    try:
        return Grupo.model_validate(servico.obter_grupo(db, usuario, grupo_id))
    except servico.NaoEncontrado as erro:
        raise _nao_encontrada("grupo", grupo_id) from erro


@router.patch(
    "/grupos/{grupo_id}",
    response_model=Grupo,
    summary="Renomeia o grupo ou troca as conversas dele",
)
def editar_grupo(
    grupo_id: int, dados: EdicaoDeGrupo, usuario: UsuarioAtual, db: Session = Depends(get_db)
) -> Grupo:
    try:
        return Grupo.model_validate(servico.editar_grupo(db, usuario, grupo_id, dados))
    except servico.NaoEncontrado as erro:
        raise _nao_encontrada("grupo", grupo_id) from erro


@router.delete(
    "/grupos/{grupo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Apaga o grupo; as conversas ficam",
)
def apagar_grupo(grupo_id: int, usuario: UsuarioAtual, db: Session = Depends(get_db)) -> Response:
    try:
        servico.apagar_grupo(db, usuario, grupo_id)
    except servico.NaoEncontrado as erro:
        raise _nao_encontrada("grupo", grupo_id) from erro
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _nao_encontrada(o_que: str, identificador: int | None) -> ErroDeNegocio:
    codigo, mensagem = {
        "conversa": ("conversa_nao_encontrada", "Conversa não encontrada"),
        "grupo": ("grupo_nao_encontrado", "Grupo não encontrado"),
    }[o_que]
    return ErroDeNegocio(
        status_code=status.HTTP_404_NOT_FOUND,
        code=codigo,
        message=mensagem,
        details={"id": identificador} if identificador is not None else None,
    )
