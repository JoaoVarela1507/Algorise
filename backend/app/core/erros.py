"""Formato único de erro da API.

Todo erro sai com a mesma forma, seja ele um 404 de rota, um 422 de validação ou
um 500 que ninguém previu:

```json
{
  "erro": {
    "code": "nao_encontrado",
    "message": "Trilha não encontrada",
    "details": {"slug": "python"},
    "request_id": "0f9c…"
  }
}
```

A divisão de trabalho entre os três campos é o que faz isso valer a pena:

- `code` é estável e em inglês — é dele que o **código** do frontend decide o que
  fazer (mandar para o login, mostrar o formulário de novo);
- `message` é em português e pode mudar a qualquer momento — é o que o **aluno**
  lê, e não deve ser usado em `if`;
- `details` carrega o que é específico daquele erro, como o campo que falhou.

Quem levanta o erro não precisa pensar nisso: uma `HTTPException` comum continua
funcionando e o handler traduz pelo status. Para escolher o `code` à mão, use
`ErroDeNegocio`.
"""

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Tradução de status HTTP para código estável. Cobre o que a API usa hoje; o que
# faltar cai em `erro_interno` para 5xx e `erro_na_requisicao` para 4xx.
CODIGOS = {
    status.HTTP_400_BAD_REQUEST: "requisicao_invalida",
    status.HTTP_401_UNAUTHORIZED: "nao_autenticado",
    status.HTTP_403_FORBIDDEN: "sem_permissao",
    status.HTTP_404_NOT_FOUND: "nao_encontrado",
    status.HTTP_409_CONFLICT: "conflito",
    status.HTTP_413_CONTENT_TOO_LARGE: "corpo_grande_demais",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "dados_invalidos",
    status.HTTP_429_TOO_MANY_REQUESTS: "limite_excedido",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "erro_interno",
    status.HTTP_503_SERVICE_UNAVAILABLE: "servico_indisponivel",
}


class Erro(BaseModel):
    """O conteúdo do campo `erro`."""

    code: str = Field(description="Código estável; é nele que o código do cliente decide")
    message: str = Field(description="Mensagem em português, para mostrar ao aluno")
    details: dict[str, Any] | None = Field(
        default=None, description="O que é específico deste erro, como o campo que falhou"
    )
    request_id: str | None = Field(
        default=None, description="Id da requisição, o mesmo que aparece no log"
    )


class RespostaDeErro(BaseModel):
    """Corpo de qualquer resposta de erro. Existe para o OpenAPI documentá-lo."""

    erro: Erro


class ErroDeNegocio(HTTPException):
    """`HTTPException` com `code` e `details` escolhidos por quem levanta.

    Use quando o frontend precisa distinguir dois erros de mesmo status — por
    exemplo, e-mail já cadastrado e username já cadastrado, ambos 409.
    """

    def __init__(
        self,
        status_code: int,
        *,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.code = code
        self.details = details


def registrar_handlers(app: FastAPI) -> None:
    """Liga os três handlers. Chamado uma vez, na criação da aplicação."""
    app.add_exception_handler(HTTPException, _erro_http)
    app.add_exception_handler(RequestValidationError, _erro_de_validacao)
    app.add_exception_handler(Exception, _erro_nao_tratado)


async def _erro_http(request: Request, excecao: Exception) -> JSONResponse:
    assert isinstance(excecao, HTTPException)

    mensagem = excecao.detail if isinstance(excecao.detail, str) else "Algo deu errado."
    detalhes = excecao.detail if isinstance(excecao.detail, dict) else None

    return _resposta(
        request,
        status_code=excecao.status_code,
        code=getattr(excecao, "code", None) or _codigo_do_status(excecao.status_code),
        message=mensagem,
        details=getattr(excecao, "details", None) or detalhes,
        headers=excecao.headers,
    )


async def _erro_de_validacao(request: Request, excecao: Exception) -> JSONResponse:
    """422 do Pydantic, achatado para o formato único.

    O formato do FastAPI é uma lista de objetos com `loc`, `msg` e `type`; útil
    para depurar, ilegível para exibir. Aqui a primeira mensagem vira o
    `message`, e a lista por campo fica em `details.campos`.
    """
    assert isinstance(excecao, RequestValidationError)

    campos = [
        {
            # `loc` começa com "body"/"query"; o que interessa é o resto.
            "campo": ".".join(str(parte) for parte in erro["loc"][1:]) or "corpo",
            "mensagem": erro["msg"],
            "tipo": erro["type"],
        }
        for erro in excecao.errors()
    ]

    primeiro = campos[0] if campos else {"campo": "corpo", "mensagem": "Dados inválidos"}

    return _resposta(
        request,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="dados_invalidos",
        message=f"{primeiro['campo']}: {primeiro['mensagem']}",
        details={"campos": campos},
    )


async def _erro_nao_tratado(request: Request, excecao: Exception) -> JSONResponse:
    """Qualquer exceção que escapou.

    O que aconteceu vai para o log com o id da requisição; para fora vai só o id.
    Stack trace e mensagem de exceção costumam conter caminho de arquivo, SQL e
    às vezes dado de usuário.
    """
    logger.exception(
        "Erro não tratado em %s %s (request_id=%s)",
        request.method,
        request.url.path,
        _request_id(request),
    )

    return _resposta(
        request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="erro_interno",
        message="Algo deu errado do nosso lado. Tente de novo em instantes.",
    )


def _resposta(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    corpo = RespostaDeErro(
        erro=Erro(code=code, message=message, details=details, request_id=_request_id(request))
    )
    return JSONResponse(
        status_code=status_code,
        content=corpo.model_dump(exclude_none=True),
        headers=headers,
    )


def _codigo_do_status(status_code: int) -> str:
    if status_code in CODIGOS:
        return CODIGOS[status_code]
    return "erro_interno" if status_code >= 500 else "erro_na_requisicao"


def _request_id(request: Request) -> str | None:
    """Posto pelo middleware de `request_id`; None quando ele não rodou."""
    return getattr(request.state, "request_id", None)
