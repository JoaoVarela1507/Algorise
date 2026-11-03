"""Centro de notificações (#37)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class NotificacaoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: str
    titulo: str
    mensagem: str
    dados: dict[str, Any]
    lida_em: datetime | None = None
    criado_em: datetime


class ContagemDeNotificacoes(BaseModel):
    nao_lidas: int


class Marcadas(BaseModel):
    marcadas: int
