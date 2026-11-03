"""Contrato da parte REST do chat: conversas, histórico, busca e grupos (#33)."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.enums import PapelMensagem

Titulo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
NomeDoGrupo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class NovaConversa(BaseModel):
    # Com a primeira mensagem, o título sai dela; sem nada, "Nova conversa".
    primeira_mensagem: str | None = Field(default=None, max_length=4000)
    titulo: Titulo | None = None


class EdicaoDeConversa(BaseModel):
    titulo: Titulo | None = None
    arquivada: bool | None = None
    # `null` tira a conversa do grupo.
    grupo_id: int | None = None


class ConversaResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    arquivada: bool
    grupo_id: int | None = None
    criado_em: datetime
    atualizado_em: datetime


class Anexo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    # `texto`, `pdf` ou `imagem`.
    tipo: str
    tamanho: int


class Mensagem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    papel: PapelMensagem
    conteudo: str
    incompleta: bool
    criado_em: datetime
    anexos: list[Anexo] = []


class NovoGrupo(BaseModel):
    nome: NomeDoGrupo
    conversa_ids: list[int] = Field(default=[], max_length=200)


class EdicaoDeGrupo(BaseModel):
    nome: NomeDoGrupo | None = None
    # A lista inteira: as que saem dela deixam o grupo.
    conversa_ids: list[int] | None = Field(default=None, max_length=200)


class Grupo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    conversas: list[ConversaResumo]
    criado_em: datetime


class Sugestao(BaseModel):
    texto: str
    # `conversa`: retomar uma conversa recente; `trilha`: puxar assunto do
    # passo em que o aluno está.
    origem: str
    conversa_id: int | None = None
