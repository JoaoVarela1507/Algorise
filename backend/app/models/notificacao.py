"""Notificações do aluno (#37): conquistas, certificados e o aviso do streak."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Notificacao(Base, TimestampMixin):
    """Fica gravada para o centro de notificações mostrar o que chegou offline."""

    __tablename__ = "notificacoes"
    __table_args__ = (Index("ix_notificacoes_usuario_lida", "usuario_id", "lida_em"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    # O nome do evento: `conquista.desbloqueada`, `certificado.liberado`, `streak.risco`.
    tipo: Mapped[str] = mapped_column(String(40))
    titulo: Mapped[str] = mapped_column(String(120))
    mensagem: Mapped[str] = mapped_column(String(300))
    # O que a tela precisa para levar ao lugar certo (id do certificado, nível...).
    dados: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    lida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
