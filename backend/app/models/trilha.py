"""Catálogo: trilha, seus módulos e as atividades de cada módulo."""

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import TipoAtividade


class Trilha(Base, TimestampMixin):
    __tablename__ = "trilhas"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Usado na URL: /trilhas/introducao-python
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    nome: Mapped[str] = mapped_column(String(200))
    disciplina: Mapped[str] = mapped_column(String(200))
    categoria: Mapped[str | None] = mapped_column(String(80))
    # 1 a 8; o filtro da tela 25 consulta por aqui.
    periodo: Mapped[int | None] = mapped_column(index=True)
    descricao: Mapped[str | None] = mapped_column(Text)
    publicada: Mapped[bool] = mapped_column(default=False, index=True)

    modulos: Mapped[list["Modulo"]] = relationship(
        back_populates="trilha", cascade="all, delete-orphan", order_by="Modulo.ordem"
    )


class Modulo(Base, TimestampMixin):
    """Um passo do caminho de bolinhas da tela 26."""

    __tablename__ = "modulos"
    __table_args__ = (UniqueConstraint("trilha_id", "ordem", name="uq_modulos_trilha_ordem"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    trilha_id: Mapped[int] = mapped_column(ForeignKey("trilhas.id", ondelete="CASCADE"), index=True)
    ordem: Mapped[int]
    titulo: Mapped[str] = mapped_column(String(200))
    descricao: Mapped[str | None] = mapped_column(Text)
    video_url: Mapped[str | None] = mapped_column(String(500))

    trilha: Mapped[Trilha] = relationship(back_populates="modulos")
    atividades: Mapped[list["Atividade"]] = relationship(
        back_populates="modulo", cascade="all, delete-orphan", order_by="Atividade.ordem"
    )


class Atividade(Base, TimestampMixin):
    __tablename__ = "atividades"
    __table_args__ = (UniqueConstraint("modulo_id", "ordem", name="uq_atividades_modulo_ordem"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    modulo_id: Mapped[int] = mapped_column(ForeignKey("modulos.id", ondelete="CASCADE"), index=True)
    ordem: Mapped[int]
    tipo: Mapped[TipoAtividade]
    enunciado: Mapped[str] = mapped_column(Text)
    dica: Mapped[str | None] = mapped_column(Text)

    # Gabarito. Nunca deve ser serializado para o cliente antes da submissão
    # (ver #30).
    comando_esperado: Mapped[str | None] = mapped_column(String(500))
    saida_esperada: Mapped[str | None] = mapped_column(Text)
    resposta_esperada: Mapped[str | None] = mapped_column(Text)

    tempo_sugerido_segundos: Mapped[int | None]
    xp: Mapped[int] = mapped_column(default=10)

    modulo: Mapped[Modulo] = relationship(back_populates="atividades")
