"""Conversas do chat com IA e suas mensagens (telas 21 a 23)."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import PapelMensagem


class Conversa(Base, TimestampMixin):
    __tablename__ = "conversas"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    # Sai da primeira mensagem do aluno; renomear é da #33.
    titulo: Mapped[str] = mapped_column(String(120))

    # Em ordem de envio: é a ordem em que elas voltam para o modelo como
    # contexto.
    mensagens: Mapped[list["MensagemChat"]] = relationship(
        back_populates="conversa", cascade="all, delete-orphan", order_by="MensagemChat.id"
    )


class MensagemChat(Base):
    """Uma fala da conversa. Não muda depois de gravada."""

    __tablename__ = "mensagens_chat"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversa_id: Mapped[int] = mapped_column(
        ForeignKey("conversas.id", ondelete="CASCADE"), index=True
    )
    papel: Mapped[PapelMensagem]
    conteudo: Mapped[str] = mapped_column(Text)
    # Resposta do assistente que parou no meio: a IA caiu ou o aluno fechou a
    # aba. O que chegou a ser gerado fica, marcado, em vez de sumir.
    incompleta: Mapped[bool] = mapped_column(default=False, server_default=false())
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversa: Mapped[Conversa] = relationship(back_populates="mensagens")
