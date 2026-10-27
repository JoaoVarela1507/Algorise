"""Chat com IA (telas 21 a 23): a mensagem do aluno e a resposta em streaming."""

import json
import logging
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any

import anyio
from fastapi import APIRouter, Depends, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import UsuarioAtual
from app.core.database import get_db, get_fabrica_de_sessoes
from app.core.erros import ErroDeNegocio, RespostaDeErro
from app.core.rate_limit import LimiteDoChat
from app.ia import IAIndisponivel, ProvedorIA, get_provedor_ia
from app.schemas.chat import NovaMensagem
from app.services import chat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

IA_FORA = "O tutor está fora do ar agora. Tente de novo em instantes."

DESCRICAO_DO_STREAMING = """\
Responde em `text/event-stream`, um evento por pedaço da resposta:

| Evento | Dados | Quando |
| --- | --- | --- |
| `chat.conversa` | `conversa_id`, `titulo`, `mensagem_id` | primeiro, com a pergunta já gravada |
| `chat.token` | `texto` | a cada pedaço da resposta |
| `chat.fim` | `mensagem_id` | resposta completa e gravada |
| `chat.erro` | `code`, `message`, `mensagem_id` | a IA parou no meio; o parcial fica gravado |

A IA fora do ar **antes** do primeiro pedaço responde 503 no formato de erro da
API, sem gravar a pergunta: o aluno tenta de novo sem deixar pergunta órfã no
histórico.
"""


@router.post(
    "/mensagens",
    summary="Envia uma mensagem ao tutor e recebe a resposta em streaming",
    description=DESCRICAO_DO_STREAMING,
    dependencies=[LimiteDoChat],
    response_class=StreamingResponse,
    responses={
        200: {"content": {"text/event-stream": {}}, "description": "Resposta em streaming"},
        404: {"model": RespostaDeErro, "description": "Conversa não encontrada"},
        429: {"model": RespostaDeErro, "description": "Mensagens demais em pouco tempo"},
        503: {"model": RespostaDeErro, "description": "IA fora do ar"},
    },
)
async def enviar_mensagem(
    dados: NovaMensagem,
    usuario: UsuarioAtual,
    db: Session = Depends(get_db),
    fabrica: sessionmaker[Session] = Depends(get_fabrica_de_sessoes),
    provedor: ProvedorIA = Depends(get_provedor_ia),
) -> StreamingResponse:
    # O banco é síncrono: fora do event loop, para uma consulta lenta não
    # segurar o streaming dos outros alunos.
    try:
        preparo = await run_in_threadpool(
            chat.preparar, db, usuario, dados.conversa_id, dados.conteudo, dados.modo
        )
    except chat.ConversaNaoEncontrada as erro:
        # A de outro aluno responde igual à inexistente.
        raise ErroDeNegocio(
            status_code=status.HTTP_404_NOT_FOUND,
            code="conversa_nao_encontrada",
            message="Conversa não encontrada",
            details={"conversa_id": dados.conversa_id},
        ) from erro

    # Espera o primeiro pedaço antes de responder: é o que permite a IA fora
    # virar um 503 de verdade, e não um 200 que só traz erro dentro.
    fluxo = provedor.gerar(preparo.contexto, max_tokens=preparo.max_tokens)
    try:
        primeiro = await anext(fluxo, "")
    except IAIndisponivel as erro:
        logger.warning("IA indisponível antes de responder: %s", erro)
        raise ErroDeNegocio(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, code="ia_indisponivel", message=IA_FORA
        ) from erro

    conversa, pergunta = await run_in_threadpool(
        chat.registrar_pergunta, db, usuario, preparo.conversa_id, dados.conteudo
    )
    return StreamingResponse(
        transmitir(
            fluxo,
            primeiro,
            fabrica,
            {"conversa_id": conversa.id, "titulo": conversa.titulo, "mensagem_id": pergunta.id},
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # Sem isso, um nginx na frente junta a resposta inteira antes de
            # repassar, e o streaming vira espera.
            "X-Accel-Buffering": "no",
        },
    )


async def transmitir(
    fluxo: AsyncGenerator[str],
    primeiro: str,
    fabrica: sessionmaker[Session],
    conversa: dict[str, Any],
) -> AsyncIterator[str]:
    """Repassa os pedaços ao aluno e grava a resposta no fim, completa ou não.

    O `finally` cobre os três finais: a IA terminou, a IA caiu no meio, e o
    aluno fechou a aba (o Starlette cancela o gerador). Nos dois últimos, o que
    já foi gerado fica gravado como incompleto.
    """
    partes: list[str] = []
    concluida = False
    resposta_id: int | None = None
    try:
        yield evento("chat.conversa", conversa)
        if primeiro:
            partes.append(primeiro)
            yield evento("chat.token", {"texto": primeiro})
        async for pedaco in fluxo:
            partes.append(pedaco)
            yield evento("chat.token", {"texto": pedaco})
        concluida = True
    except IAIndisponivel as erro:
        logger.warning("IA parou no meio da resposta: %s", erro)
    finally:
        await fluxo.aclose()
        # Blindado: no cancelamento por desconexão, o `await` seguinte também
        # seria cancelado, e a resposta parcial se perderia.
        with anyio.CancelScope(shield=True):
            resposta_id = await run_in_threadpool(
                chat.registrar_resposta,
                fabrica,
                conversa["conversa_id"],
                "".join(partes),
                incompleta=not concluida,
            )

    if concluida:
        yield evento("chat.fim", {"mensagem_id": resposta_id})
    else:
        yield evento(
            "chat.erro", {"code": "ia_indisponivel", "message": IA_FORA, "mensagem_id": resposta_id}
        )


def evento(nome: str, dados: dict[str, Any]) -> str:
    """Um evento SSE. `ensure_ascii=False` para o acento não virar `\\u00e7`."""
    return f"event: {nome}\ndata: {json.dumps(dados, ensure_ascii=False)}\n\n"
