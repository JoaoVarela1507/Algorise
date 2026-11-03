"""Contrato do WebSocket (`WS /api/v1/ws`, #35).

Toda mensagem é um objeto JSON com `tipo`. O cliente abre a conexão e manda
`autenticar` no primeiro frame; o token não vai na query string, que acaba em
log de proxy. Depois disso ele se inscreve nos canais que quer ouvir:

- `chat:{conversa_id}`: só as conversas do aluno;
- `ranking:geral` e `ranking:{trilha_id}`: qualquer aluno logado;
- `notificacoes:{usuario_id}`: só o próprio aluno.

Os eventos chegam em `evento`, com o canal, o nome do evento e o `payload`.

O chat também anda por aqui (#36): `chat.mensagem.enviar` pergunta ao tutor, e a
resposta chega no canal `chat:{conversa_id}` como `chat.conversa`, `chat.token`
e, no fim, `chat.fim`, `chat.parado` ou `chat.erro`. Todas as abas inscritas na
conversa veem a mesma geração. `chat.parar` interrompe, e `chat.digitando` avisa
as outras abas.

Os dois lados ficam no OpenAPI (`MensagemDoCliente` e `MensagemDoServidor`),
para os tipos TypeScript saírem gerados como os das rotas REST.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, RootModel

from app.schemas.chat import NovaMensagem

Canal = Annotated[str, Field(min_length=1, max_length=80, pattern=r"^[a-z_]+:[a-z0-9_]+$")]


# --- do cliente ---------------------------------------------------------------------------


class Autenticar(BaseModel):
    tipo: Literal["autenticar"]
    token: str = Field(max_length=4000)


class Inscrever(BaseModel):
    tipo: Literal["inscrever"]
    canal: Canal


class Cancelar(BaseModel):
    tipo: Literal["cancelar"]
    canal: Canal


class Ping(BaseModel):
    tipo: Literal["ping"]


class Pong(BaseModel):
    tipo: Literal["pong"]


class EnviarMensagemDoChat(NovaMensagem):
    """A pergunta ao tutor, com os mesmos campos do `POST /chat/mensagens`."""

    tipo: Literal["chat.mensagem.enviar"]


class PararChat(BaseModel):
    tipo: Literal["chat.parar"]
    conversa_id: int


class DigitandoNoChat(BaseModel):
    tipo: Literal["chat.digitando"]
    conversa_id: int


class MensagemDoCliente(RootModel):
    root: Annotated[
        Autenticar
        | Inscrever
        | Cancelar
        | Ping
        | Pong
        | EnviarMensagemDoChat
        | PararChat
        | DigitandoNoChat,
        Field(discriminator="tipo"),
    ]


# --- do servidor --------------------------------------------------------------------------


class Autenticado(BaseModel):
    tipo: Literal["autenticado"] = "autenticado"
    usuario_id: int


class Inscrito(BaseModel):
    tipo: Literal["inscrito"] = "inscrito"
    canal: str


class Cancelado(BaseModel):
    tipo: Literal["cancelado"] = "cancelado"
    canal: str


class Evento(BaseModel):
    tipo: Literal["evento"] = "evento"
    canal: str
    # O nome do evento no canal, como `ranking.atualizado` ou `chat.token`.
    evento: str
    payload: dict[str, Any] = {}


class PingDoServidor(BaseModel):
    tipo: Literal["ping"] = "ping"


class PongDoServidor(BaseModel):
    tipo: Literal["pong"] = "pong"


class ErroDoWebSocket(BaseModel):
    tipo: Literal["erro"] = "erro"
    # Os mesmos `code` estáveis da API REST: `nao_autenticado`, `canal_negado`,
    # `mensagem_invalida`, `rate_limit`, `conexoes_demais` e, no chat,
    # `conversa_nao_encontrada`, `chat_ocupado` e `ia_indisponivel`.
    code: str
    message: str


class MensagemDoServidor(RootModel):
    root: Annotated[
        Autenticado
        | Inscrito
        | Cancelado
        | Evento
        | PingDoServidor
        | PongDoServidor
        | ErroDoWebSocket,
        Field(discriminator="tipo"),
    ]
