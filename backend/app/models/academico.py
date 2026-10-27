"""Instituição, curso e ementa — o que o onboarding coleta (telas 14 e 15)."""

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import StatusEmenta


class Instituicao(Base, TimestampMixin):
    __tablename__ = "instituicoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), unique=True)
    sigla: Mapped[str | None] = mapped_column(String(20), index=True)
    uf: Mapped[str | None] = mapped_column(String(2))
    # Veio do seed, com nome conferido. Só as verificadas aparecem no
    # autocomplete: a que um aluno digitou livremente ("ufrpee") fica com ele e
    # não vira sugestão para os outros.
    verificada: Mapped[bool] = mapped_column(default=False, server_default=false())

    cursos: Mapped[list["Curso"]] = relationship(back_populates="instituicao")


class Curso(Base, TimestampMixin):
    __tablename__ = "cursos"
    __table_args__ = (
        UniqueConstraint("instituicao_id", "nome", name="uq_cursos_instituicao_nome"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    instituicao_id: Mapped[int] = mapped_column(
        ForeignKey("instituicoes.id", ondelete="CASCADE"), index=True
    )
    nome: Mapped[str] = mapped_column(String(200))
    total_periodos: Mapped[int] = mapped_column(default=8)
    # Mesma regra da instituição: só o curso do seed aparece no autocomplete.
    verificado: Mapped[bool] = mapped_column(default=False, server_default=false())

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
    # Relativo a `diretorio_midia`, fora da pasta pública dos avatares.
    arquivo_path: Mapped[str] = mapped_column(String(500))
    nome_original: Mapped[str | None] = mapped_column(String(255))
    tamanho_bytes: Mapped[int | None]
    # SHA-256 do PDF: a mesma ementa enviada de novo (pelo mesmo aluno ou por
    # um colega de curso) reaproveita o texto já extraído.
    hash_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    paginas: Mapped[int | None]
    status: Mapped[StatusEmenta] = mapped_column(default=StatusEmenta.pendente, index=True)
    # Guardado para não reprocessar o mesmo PDF a cada tentativa.
    texto_extraido: Mapped[str | None] = mapped_column(Text)
    erro: Mapped[str | None] = mapped_column(Text)
