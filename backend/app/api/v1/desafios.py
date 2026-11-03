"""Desafio de código (#34): enunciado, execução na sandbox e resultado.

`POST /desafios/{id}/execucoes` só grava e enfileira (202); o worker roda o
código num container isolado (ver `app/sandbox`), e a tela acompanha por
`GET /execucoes/{id}` até sair de `na_fila`/`executando`.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import UsuarioAtual
from app.core.config import settings
from app.core.database import get_db
from app.core.erros import ErroDeNegocio, RespostaDeErro
from app.core.fila import Fila, get_fila
from app.core.rate_limit import verificar
from app.models import Atividade
from app.schemas.desafios import (
    CasoPublico,
    Desafio,
    ExecucaoNaFila,
    ExecucaoSaida,
    NovaExecucao,
)
from app.services import desafios as servico

router = APIRouter(tags=["desafios"])

NAO_ENCONTRADO = {404: {"model": RespostaDeErro, "description": "Não encontrado"}}


@router.get(
    "/desafios/{desafio_id}",
    response_model=Desafio,
    summary="Enunciado, dica e casos de teste públicos",
    responses=NAO_ENCONTRADO,
)
def obter_desafio(desafio_id: int, db: Session = Depends(get_db)) -> Desafio:
    atividade = _desafio(db, desafio_id)
    todos = servico.casos(db, atividade.id)
    return Desafio(
        id=atividade.id,
        enunciado=atividade.enunciado,
        dica=atividade.dica,
        xp=atividade.xp,
        casos_publicos=[CasoPublico.model_validate(c) for c in todos if c.publico],
        total_casos=len(todos),
    )


@router.post(
    "/desafios/{desafio_id}/execucoes",
    response_model=ExecucaoNaFila,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Envia o código para rodar na sandbox",
    description="Responde na hora com o id; o resultado sai em `GET /execucoes/{id}`.",
    responses={
        **NAO_ENCONTRADO,
        429: {"model": RespostaDeErro, "description": "Execuções demais em pouco tempo"},
    },
)
def executar_desafio(
    desafio_id: int,
    dados: NovaExecucao,
    usuario: UsuarioAtual,
    db: Session = Depends(get_db),
    fila: Fila = Depends(get_fila),
) -> ExecucaoNaFila:
    atividade = _desafio(db, desafio_id)
    limite = verificar(
        f"execucao:usuario:{usuario.id}",
        limite=settings.rate_limit_execucoes_requisicoes,
        janela=settings.rate_limit_execucoes_janela,
    )
    if not limite.permitido:
        raise ErroDeNegocio(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="rate_limit",
            message="Execuções demais em pouco tempo. Espere um pouco e tente de novo.",
            headers={"Retry-After": str(limite.reiniciar_em)},
        )
    execucao = servico.criar_execucao(db, usuario, atividade, dados.codigo)
    fila.execucao(execucao.id)
    return ExecucaoNaFila(id=execucao.id, status=execucao.status)


@router.get(
    "/execucoes/{execucao_id}",
    response_model=ExecucaoSaida,
    summary="Status e resultado de uma execução",
    responses=NAO_ENCONTRADO,
)
def obter_execucao(
    execucao_id: str, usuario: UsuarioAtual, db: Session = Depends(get_db)
) -> ExecucaoSaida:
    try:
        return ExecucaoSaida.model_validate(servico.do_aluno(db, usuario, execucao_id))
    except servico.ExecucaoNaoEncontrada as erro:
        raise ErroDeNegocio(
            status_code=status.HTTP_404_NOT_FOUND,
            code="execucao_nao_encontrada",
            message="Execução não encontrada",
            details={"id": execucao_id},
        ) from erro


def _desafio(db: Session, desafio_id: int) -> Atividade:
    try:
        return servico.obter(db, desafio_id)
    except servico.DesafioNaoEncontrado as erro:
        raise ErroDeNegocio(
            status_code=status.HTTP_404_NOT_FOUND,
            code="desafio_nao_encontrado",
            message="Desafio não encontrado",
            details={"id": desafio_id},
        ) from erro
