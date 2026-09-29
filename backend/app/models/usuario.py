from sqlalchemy import ForeignKey, String, UniqueConstraint
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
    contas_oauth: Mapped[list["ContaOAuth"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan"
    )


class ContaOAuth(Base, TimestampMixin):
    """Vínculo entre a conta do Algorise e um login social (#10).

    Existe como tabela à parte, e não como colunas em `usuarios`, porque o mesmo
    aluno pode entrar pelo GitHub e pelo Google — e porque o par
    (provedor, id no provedor) é o que precisa ser único, não o e-mail: e-mail
    do GitHub muda, o id não.
    """

    __tablename__ = "contas_oauth"
    __table_args__ = (UniqueConstraint("provedor", "provedor_id", name="uq_contas_oauth_provedor"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    provedor: Mapped[str] = mapped_column(String(20))
    provedor_id: Mapped[str] = mapped_column(String(100))
    # Guardado para diagnóstico: é o e-mail que o provedor informou na hora do
    # vínculo, que pode não ser mais o do `usuarios`.
    email: Mapped[str | None] = mapped_column(String(255))

    usuario: Mapped["Usuario"] = relationship(back_populates="contas_oauth")
