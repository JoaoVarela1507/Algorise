"""Contrato do chat com IA (telas 21 a 23)."""

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.core.config import settings
from app.models.enums import ModoResposta

__all__ = ["NovaMensagem"]


class NovaMensagem(BaseModel):
    conversa_id: int | None = Field(
        default=None, description="Conversa em que a mensagem entra. Sem ele, abre uma nova."
    )
    conteudo: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, min_length=1, max_length=settings.chat_maximo_caracteres
        ),
    ] = Field(description="A pergunta do aluno")
    modo: ModoResposta = Field(
        default=ModoResposta.medio, description="Quanto o tutor se aprofunda na resposta"
    )
