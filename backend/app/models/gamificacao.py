"""XP, streak e certificados — o que aparece nas telas 16, 20 e 38."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import OrigemXP


class XPEvento(Base, TimestampMixin):
    """Fonte da verdade do XP. `usuarios.xp_total` é só um cache disso."""

    __tablename__ = "xp_eventos"
    __table_args__ = (Index("ix_xp_eventos_usuario_data", "usuario_id", "criado_em"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    origem: Mapped[OrigemXP]
    # Id do que gerou o XP (atividade, módulo, trilha...). Sem FK porque a
    # origem varia.
    referencia_id: Mapped[int | None]
    valor: Mapped[int]


class Streak(Base, TimestampMixin):
    __tablename__ = "streaks"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), unique=True
    )
    dias_consecutivos: Mapped[int] = mapped_column(default=0)
    maior_sequencia: Mapped[int] = mapped_column(default=0)
    ultimo_acesso: Mapped[date | None] = mapped_column(Date)

    usuario: Mapped["Usuario"] = relationship(back_populates="streak")  # noqa: F821


class Parceiro(Base, TimestampMixin):
    """Instituição que certifica as trilhas dela (#32).

    Só trilha de parceiro emite certificado: é o aviso da tela 20.
    """

    __tablename__ = "parceiros"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), unique=True)
    site: Mapped[str | None] = mapped_column(String(300))


class Certificado(Base, TimestampMixin):
    """Emitido ao concluir 100% de uma trilha de parceiro (#32).

    O nome do aluno, da trilha, a disciplina, a carga horária e o parceiro são
    copiados na emissão: a validação pública mostra o que o certificado disse
    no dia, mesmo que a trilha ou o nome do aluno mudem depois.
    """

    __tablename__ = "certificados"
    __table_args__ = (
        UniqueConstraint("usuario_id", "trilha_id", name="uq_certificados_usuario_trilha"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    trilha_id: Mapped[int] = mapped_column(ForeignKey("trilhas.id", ondelete="CASCADE"))
    # Usado na validação pública: `ALG-7K3Q-9XWM`, sem letra que confunda.
    codigo: Mapped[str] = mapped_column(String(40), unique=True)
    parceiro: Mapped[str | None] = mapped_column(String(120))
    emitido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    nome_aluno: Mapped[str | None] = mapped_column(String(200))
    nome_trilha: Mapped[str | None] = mapped_column(String(200))
    disciplina: Mapped[str | None] = mapped_column(String(200))
    carga_horaria: Mapped[int | None]
