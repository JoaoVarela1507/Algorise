"""Instituição, curso e ementa — o que o onboarding coleta (telas 14 e 15)."""

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import StatusEmenta


class Instituicao(Base, TimestampMixin):
    __tablename__ = "instituicoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), unique=True)
    sigla: Mapped[str | None] = mapped_column(String(20), index=True)
    uf: Mapped[str | None] = mapped_column(String(2))

    cursos: Mapped[list["Curso"]] = relationship(back_populates="instituicao")


class Curso(Base, TimestampMixin):
    __tablename__ = "cursos"
    __table_args__ = (UniqueConstraint("instituicao_id", "nome", name="uq_cursos_instituicao_nome"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    instituicao_id: Mapped[int] = mapped_column(
        ForeignKey("instituicoes.id", ondelete="CASCADE"), index=True
    )
    nome: Mapped[str] = mapped_column(String(200))
    total_periodos: Mapped[int] = mapped_column(default=8)

    instituicao: Mapped[Instituicao] = relationship(back_populates="cursos")


class Ementa(Base, TimestampMixin):
    """PDF enviado pelo aluno e o resultado da extração (#38)."""

    __tablename__ = "ementas"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    curso_id: Mapped[int | None] = mapped_column(ForeignKey("cursos.id", ondelete="SET NULL"))
    periodo: Mapped[int | None]
    arquivo_path: Mapped[str] = mapped_column(String(500))
    status: Mapped[StatusEmenta] = mapped_column(default=StatusEmenta.pendente, index=True)
    # Guardado para não reprocessar o mesmo PDF a cada tentativa.
    texto_extraido: Mapped[str | None] = mapped_column(Text)
    erro: Mapped[str | None] = mapped_column(Text)
