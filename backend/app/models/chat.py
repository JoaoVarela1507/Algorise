"""Conversas do chat com IA e suas mensagens (telas 21 a 23)."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, false, func, literal_column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import PapelMensagem


class GrupoChat(Base, TimestampMixin):
    """Grupo temático de conversas que o aluno monta (tela 23, #33)."""

    __tablename__ = "grupos_chat"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    nome: Mapped[str] = mapped_column(String(80))

    conversas: Mapped[list["Conversa"]] = relationship(back_populates="grupo")


class Conversa(Base, TimestampMixin):
    __tablename__ = "conversas"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    # Sai da primeira mensagem do aluno; o aluno pode renomear.
    titulo: Mapped[str] = mapped_column(String(120))
    # Some do histórico sem apagar: volta filtrando por arquivadas.
    arquivada: Mapped[bool] = mapped_column(default=False, server_default=false())
    # Uma conversa fica em um grupo, no máximo. Apagar o grupo solta as conversas.
    grupo_id: Mapped[int | None] = mapped_column(
        ForeignKey("grupos_chat.id", ondelete="SET NULL"), index=True
    )

    # O que saiu da janela de contexto, resumido pelo modelo (#33). Vai para o
    # tutor antes das últimas mensagens; `resumo_ate_id` é a última que entrou nele.
    resumo: Mapped[str | None] = mapped_column(Text)
    resumo_ate_id: Mapped[int | None]

    grupo: Mapped[GrupoChat | None] = relationship(back_populates="conversas")

    # Em ordem de envio: é a ordem em que elas voltam para o modelo como
    # contexto.
    mensagens: Mapped[list["MensagemChat"]] = relationship(
        back_populates="conversa", cascade="all, delete-orphan", order_by="MensagemChat.id"
    )


class MensagemChat(Base):
    """Uma fala da conversa. Não muda depois de gravada."""

    __tablename__ = "mensagens_chat"
    __table_args__ = (
        # Busca por palavra-chave no histórico (#33): o full-text do PostgreSQL,
        # em português. No SQLite dos testes o índice não existe, e a busca cai
        # num `LIKE` (ver `services/conversas.py`).
        Index(
            "ix_mensagens_chat_conteudo_busca",
            func.to_tsvector(literal_column("'portuguese'"), literal_column("conteudo")),
            postgresql_using="gin",
        ).ddl_if(dialect="postgresql"),
    )

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
    anexos: Mapped[list["AnexoChat"]] = relationship(
        back_populates="mensagem", cascade="all, delete-orphan", order_by="AnexoChat.id"
    )


class AnexoChat(Base, TimestampMixin):
    """Arquivo que o aluno manda junto com a pergunta (#33).

    Sobe antes (`POST /chat/anexos`) e se liga à mensagem quando ela é enviada.
    O arquivo fica em `diretorio_midia/chat`, fora da pasta pública; o texto
    extraído (do código, do texto ou do PDF) é o que vai para o modelo.
    """

    __tablename__ = "anexos_chat"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    mensagem_id: Mapped[int | None] = mapped_column(
        ForeignKey("mensagens_chat.id", ondelete="CASCADE"), index=True
    )
    nome: Mapped[str] = mapped_column(String(200))
    # `texto`, `pdf` ou `imagem`: decidido pelo conteúdo, não pela extensão.
    tipo: Mapped[str] = mapped_column(String(10))
    tamanho: Mapped[int]
    arquivo: Mapped[str] = mapped_column(String(100))
    texto: Mapped[str | None] = mapped_column(Text)

    mensagem: Mapped[MensagemChat | None] = relationship(back_populates="anexos")
