"""Identificação e cronometragem de cada requisição.

Serve para uma pergunta que sempre aparece: "o aluno viu esse erro, o que
aconteceu?". Com o id no corpo do erro e no log, a resposta é um `grep`.

O id vem de fora quando já existe (proxy ou frontend que manda `X-Request-Id`),
para a mesma requisição ter o mesmo id na borda e aqui dentro. Como é um valor
que veio do cliente, ele é sanado antes de entrar em qualquer log.
"""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.requisicao")

CABECALHO_ID = "X-Request-Id"
CABECALHO_TEMPO = "X-Response-Time-Ms"

# Teto para o id que vem de fora: o suficiente para um UUID ou um trace id, e
# curto o bastante para não inflar log com um header de 8 KB.
MAXIMO_ID = 64


class Rastreio(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = _id_da_requisicao(request)
        # Os handlers de erro leem daqui para pôr o id no corpo.
        request.state.request_id = request_id

        inicio = time.perf_counter()
        try:
            resposta = await call_next(request)
        except Exception:
            # O handler de 500 loga o que houve; aqui fica só o tempo, para uma
            # requisição que explodiu não sumir da contagem.
            duracao = _milissegundos(inicio)
            logger.warning(
                "%s %s falhou em %sms (request_id=%s)",
                request.method,
                request.url.path,
                duracao,
                request_id,
            )
            raise

        duracao = _milissegundos(inicio)
        resposta.headers[CABECALHO_ID] = request_id
        resposta.headers[CABECALHO_TEMPO] = str(duracao)

        # Uma linha por requisição. `url.path` sem a query: ela carrega busca do
        # aluno e, em rota de recuperação de senha, carregaria o token.
        logger.info(
            "%s %s %s %sms (request_id=%s)",
            request.method,
            request.url.path,
            resposta.status_code,
            duracao,
            request_id,
        )
        return resposta


def _id_da_requisicao(request: Request) -> str:
    recebido = request.headers.get(CABECALHO_ID, "")
    limpo = "".join(c for c in recebido if c.isalnum() or c in "-_")[:MAXIMO_ID]
    return limpo or uuid.uuid4().hex


def _milissegundos(inicio: float) -> int:
    return int((time.perf_counter() - inicio) * 1000)
