"""Vault das skills de IA (#200): o conhecimento que as skills consultam.

Um documento é uma transcrição de vídeo (ligada ao módulo) ou o prompt de uma
skill. Ele é dividido em trechos, e cada trecho guarda o embedding para a busca
por similaridade, que no PostgreSQL é feita pelo pgvector.
"""

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.ia.base import DIMENSOES_EMBEDDING
from app.models.base import Base, TimestampMixin
from app.models.enums import OrigemVault


class DocumentoVault(Base, TimestampMixin):
    __tablename__ = "vault_documentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    origem: Mapped[OrigemVault]
    # Identifica o documento na reingestão: "modulo:3", "skill:tutor". Ingerir
    # de novo a mesma chave substitui os trechos, em vez de duplicar.
    chave: Mapped[str] = mapped_column(String(120), unique=True)
    titulo: Mapped[str] = mapped_column(String(200))
    # Transcrição: o vídeo é o do módulo. Apagar o módulo apaga a transcrição.
    modulo_id: Mapped[int | None] = mapped_column(
        ForeignKey("modulos.id", ondelete="CASCADE"), index=True
    )
    # Prompt: o nome do módulo em `app/ia/skills/`.
    skill: Mapped[str | None] = mapped_column(String(80))
    # SHA-256 do conteúdo. Igual ao guardado, a ingestão não refaz nada.
    hash_conteudo: Mapped[str] = mapped_column(String(64))
    # Sobe a cada conteúdo novo com a mesma chave.
    versao: Mapped[int] = mapped_column(default=1)

    trechos: Mapped[list["TrechoVault"]] = relationship(
        back_populates="documento", cascade="all, delete-orphan", order_by="TrechoVault.ordem"
    )


class TrechoVault(Base):
    __tablename__ = "vault_trechos"
    __table_args__ = (
        UniqueConstraint("documento_id", "ordem", name="uq_vault_trechos_documento_ordem"),
        # HNSW com distância de cosseno, a mesma que a busca ordena.
        Index(
            "ix_vault_trechos_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    documento_id: Mapped[int] = mapped_column(
        ForeignKey("vault_documentos.id", ondelete="CASCADE"), index=True
    )
    ordem: Mapped[int]
    texto: Mapped[str] = mapped_column(Text)
    # Em que segundo do vídeo o trecho começa, quando a transcrição tem tempo
    # (.srt e .vtt). Serve para a skill apontar o momento do vídeo.
    inicio_segundos: Mapped[float | None]
    # No SQLite dos testes não há pgvector: o vetor vira uma lista em JSON, e a
    # busca calcula a distância em Python (ver `app/ia/vault/busca.py`).
    embedding: Mapped[list[float]] = mapped_column(
        Vector(DIMENSOES_EMBEDDING).with_variant(JSON(), "sqlite")
    )

    documento: Mapped[DocumentoVault] = relationship(back_populates="trechos")
