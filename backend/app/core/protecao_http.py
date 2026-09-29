"""Headers de segurança e teto de tamanho do corpo em toda resposta (#40).

É um middleware ASGI puro, não um `BaseHTTPMiddleware`, por causa do corpo: para
recusar um upload grande é preciso contar os bytes enquanto chegam, antes de a
rota ler tudo para a memória — e o `BaseHTTPMiddleware` só entrega o corpo
depois de lido.
"""

import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import settings

# A API só devolve JSON: nada de script, estilo, frame ou formulário. Se uma
# resposta for parar num navegador como página, ela não executa nada.
_CSP_DA_API = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"

# O Swagger (`/docs`) e o ReDoc carregam script e estilo de CDN; com a CSP da API
# eles abririam em branco. Ficam só com os headers que não quebram nada.
_ROTAS_DE_DOCUMENTACAO = ("/docs", "/redoc", "/openapi.json")

_HEADERS_BASE = [
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"no-referrer"),
    (b"x-frame-options", b"DENY"),
    (b"cross-origin-opener-policy", b"same-origin"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
]

# Um ano. Só em produção: em desenvolvimento a API é http://localhost, e HSTS
# ali faria o navegador insistir em https numa porta que não tem TLS.
_HSTS = (b"strict-transport-security", b"max-age=31536000; includeSubDomains")

_METODOS_COM_CORPO = {"POST", "PUT", "PATCH"}


class ProtecaoHTTP:
    def __init__(self, app: ASGIApp, *, tamanho_maximo: int | None = None) -> None:
        self.app = app
        self.tamanho_maximo = tamanho_maximo or settings.tamanho_maximo_requisicao

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = self._headers_para(scope["path"])

        async def enviar_com_headers(mensagem: Message) -> None:
            if mensagem["type"] == "http.response.start":
                existentes = {nome for nome, _ in mensagem.get("headers", [])}
                mensagem["headers"] = [
                    *mensagem.get("headers", []),
                    *((n, v) for n, v in headers if n not in existentes),
                ]
            await send(mensagem)

        if scope["method"] not in _METODOS_COM_CORPO:
            await self.app(scope, receive, enviar_com_headers)
            return

        # Com `Content-Length`, dá para recusar sem ler um byte.
        declarado = _content_length(scope)
        if declarado is not None and declarado > self.tamanho_maximo:
            await self._recusar(enviar_com_headers)
            return

        # Sem ele (envio em partes), conta enquanto chega. Estourou: para de ler
        # e responde 413, em vez de deixar a rota consumir o resto.
        recebidos = 0
        estourou = False

        async def receber_contando() -> Message:
            nonlocal recebidos, estourou
            mensagem = await receive()
            if mensagem["type"] == "http.request":
                recebidos += len(mensagem.get("body", b""))
                if recebidos > self.tamanho_maximo:
                    estourou = True
                    return {"type": "http.disconnect"}
            return mensagem

        resposta_iniciada = False

        async def enviar_se_nao_estourou(mensagem: Message) -> None:
            nonlocal resposta_iniciada
            if estourou:
                return
            resposta_iniciada = resposta_iniciada or mensagem["type"] == "http.response.start"
            await enviar_com_headers(mensagem)

        try:
            await self.app(scope, receber_contando, enviar_se_nao_estourou)
        except Exception:
            # A rota viu o "disconnect" no meio do corpo e levantou. Não é erro
            # da aplicação: é o estouro, e a resposta certa é o 413 abaixo.
            if not estourou:
                raise

        if estourou and not resposta_iniciada:
            await self._recusar(enviar_com_headers)

    def _headers_para(self, caminho: str) -> list[tuple[bytes, bytes]]:
        headers = list(_HEADERS_BASE)
        if not caminho.startswith(_ROTAS_DE_DOCUMENTACAO):
            headers.append((b"content-security-policy", _CSP_DA_API.encode()))
        if settings.environment == "production":
            headers.append(_HSTS)
        return headers

    async def _recusar(self, send: Send) -> None:
        megabytes = self.tamanho_maximo // (1024 * 1024)
        corpo = json.dumps(
            {"detail": f"A requisição passa do limite de {megabytes} MB."},
            ensure_ascii=False,
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(corpo)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": corpo})


def _content_length(scope: Scope) -> int | None:
    for nome, valor in scope.get("headers", []):
        if nome == b"content-length":
            try:
                return int(valor)
            except ValueError:
                return None
    return None
