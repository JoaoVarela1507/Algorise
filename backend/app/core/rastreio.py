"""Identificação, cronometragem e métricas de cada requisição.

Serve para uma pergunta que sempre aparece: "o aluno viu esse erro, o que
aconteceu?". Com o id no corpo do erro e no log, a resposta é um `grep`.

O id vem de fora quando já existe (proxy ou frontend que manda `X-Request-Id`),
para a mesma requisição ter o mesmo id na borda e aqui dentro. Como é um valor
que veio do cliente, ele é sanado antes de entrar em qualquer log.
"""

import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core import logs, metricas

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
        # E todo log desta requisição, pelo contexto (ver `app/core/logs.py`).
        token_id = logs.request_id.set(request_id)
        token_rota = logs.rota.set(request.url.path)
        token_usuario = logs.usuario_id.set(None)

        inicio = time.perf_counter()
        try:
            try:
                resposta = await call_next(request)
            except Exception:
                # O handler de 500 loga o que houve; aqui fica só o tempo, para
                # uma requisição que explodiu não sumir da contagem.
                duracao = _milissegundos(inicio)
                metricas.observar_requisicao(request.method, _rota(request), 500, duracao / 1000)
                logger.warning(
                    "%s %s falhou em %sms",
                    request.method,
                    request.url.path,
                    duracao,
                    extra={"metodo": request.method, "duracao_ms": duracao},
                )
                raise

            duracao = _milissegundos(inicio)
            resposta.headers[CABECALHO_ID] = request_id
            resposta.headers[CABECALHO_TEMPO] = str(duracao)
            rota = _rota(request)
            metricas.observar_requisicao(request.method, rota, resposta.status_code, duracao / 1000)

            # Uma linha por requisição. `url.path` sem a query: ela carrega a
            # busca do aluno e, em rota de recuperação de senha, carregaria o token.
            logger.info(
                "%s %s %s %sms",
                request.method,
                request.url.path,
                resposta.status_code,
                duracao,
                extra={
                    "metodo": request.method,
                    "modelo_da_rota": rota,
                    "status": resposta.status_code,
                    "duracao_ms": duracao,
                    # Gravado pela autenticação (ver `get_current_user`).
                    "aluno_id": getattr(request.state, "usuario_id", None),
                },
            )
            return resposta
        finally:
            logs.request_id.reset(token_id)
            logs.rota.reset(token_rota)
            logs.usuario_id.reset(token_usuario)


def _id_da_requisicao(request: Request) -> str:
    recebido = request.headers.get(CABECALHO_ID, "")
    limpo = "".join(c for c in recebido if c.isalnum() or c in "-_")[:MAXIMO_ID]
    return limpo or uuid.uuid4().hex


def _rota(request: Request) -> str:
    """O modelo da rota (`/api/v1/trilhas/{slug}`), para a métrica não ganhar uma série por id.

    Os modelos saem do OpenAPI da própria aplicação, uma vez só: com os routers
    aninhados, a rota que o FastAPI deixa no `scope` tem o caminho relativo ao
    router dela. Caminho que não casa com nenhum (404 de varredura, arquivo de
    `/media`) vira um rótulo só.
    """
    global _modelos
    if _modelos is None:
        _modelos = _modelos_de_rota(request.app.openapi().get("paths", {}))
    caminho = request.url.path
    return next(
        (modelo for padrao, modelo in _modelos if padrao.fullmatch(caminho)), "desconhecida"
    )


_modelos: list[tuple[re.Pattern[str], str]] | None = None


def _modelos_de_rota(caminhos: dict) -> list[tuple[re.Pattern[str], str]]:
    """Os modelos do mais específico para o menos: `/ementas/atual` antes de `/ementas/{id}`."""
    modelos = sorted(caminhos, key=lambda m: (m.count("{"), -len(m)))
    return [
        (re.compile("[^/]+".join(re.escape(p) for p in re.split(r"\{[^/]+?\}", m))), m)
        for m in modelos
    ]


def _milissegundos(inicio: float) -> int:
    return int((time.perf_counter() - inicio) * 1000)
