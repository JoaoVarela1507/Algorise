from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.academico import Curso, Instituicao
from app.models.base import Base, TimestampMixin
from app.models.enums import NivelExperiencia, ProvedorOAuth, TipoTrilha


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
    instituicao: Mapped[Instituicao | None] = relationship()
    curso: Mapped[Curso | None] = relationship()
    identidades: Mapped[list["IdentidadeOAuth"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan"
    )


class IdentidadeOAuth(Base, TimestampMixin):
    """Conta do GitHub ou do Google vinculada a um aluno.

    O vínculo é pelo id do provedor, não pelo e-mail: o aluno pode trocar o e-mail
    no GitHub, e o id continua o mesmo. O e-mail só entra na primeira vez, para
    decidir entre criar a conta ou vincular a uma que já existe.
    """

    __tablename__ = "identidades_oauth"
    __table_args__ = (
        UniqueConstraint("provedor", "id_externo", name="uq_identidades_oauth_provedor_externo"),
        # Uma conta de cada provedor por aluno.
        UniqueConstraint("usuario_id", "provedor", name="uq_identidades_oauth_usuario_provedor"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    provedor: Mapped[ProvedorOAuth]
    id_externo: Mapped[str] = mapped_column(String(255))

    usuario: Mapped[Usuario] = relationship(back_populates="identidades")
