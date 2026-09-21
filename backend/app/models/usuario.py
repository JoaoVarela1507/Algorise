from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import NivelExperiencia, TipoTrilha


class Usuario(Base, TimestampMixin):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    nome_exibicao: Mapped[str] = mapped_column(String(120))
    # Nulo para contas criadas via GitHub/Google (#10).
    senha_hash: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(500))

    nivel_experiencia: Mapped[NivelExperiencia] = mapped_column(default=NivelExperiencia.baixo)
    tipo_trilha: Mapped[TipoTrilha] = mapped_column(default=TipoTrilha.guiada)

    instituicao_id: Mapped[int | None] = mapped_column(
        ForeignKey("instituicoes.id", ondelete="SET NULL")
    )
    curso_id: Mapped[int | None] = mapped_column(ForeignKey("cursos.id", ondelete="SET NULL"))
    periodo: Mapped[int | None]

    # Saldo desnormalizado: a verdade são os registros em `xp_eventos`. Existe
    # para o ranking não somar a tabela inteira a cada consulta.
    xp_total: Mapped[int] = mapped_column(default=0, index=True)

    streak: Mapped["Streak | None"] = relationship(  # noqa: F821
        back_populates="usuario", uselist=False
    )
