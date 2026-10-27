"""Instituição, curso e ementa — o que o onboarding coleta (telas 14 e 15).

A ementa vira disciplinas e assuntos (#38). Cada assunto aponta para o módulo
do catálogo que o cobre ou para a lacuna que ainda falta preencher.
"""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import StatusAssuntos, StatusEmenta, StatusLacuna

if TYPE_CHECKING:
    from app.models.trilha import Modulo


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
    # A leitura dos assuntos pela IA vem depois do texto, com status e erro
    # próprios: a IA fora do ar não invalida um PDF que foi lido.
    status_assuntos: Mapped[StatusAssuntos] = mapped_column(
        default=StatusAssuntos.pendente, server_default=StatusAssuntos.pendente.value
    )
    erro_assuntos: Mapped[str | None] = mapped_column(Text)

    disciplinas: Mapped[list["DisciplinaEmenta"]] = relationship(
        back_populates="ementa", cascade="all, delete-orphan", order_by="DisciplinaEmenta.ordem"
    )


class DisciplinaEmenta(Base):
    """Uma disciplina lida da ementa, na ordem em que aparece no documento."""

    __tablename__ = "ementa_disciplinas"
    __table_args__ = (
        UniqueConstraint("ementa_id", "ordem", name="uq_ementa_disciplinas_ementa_ordem"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ementa_id: Mapped[int] = mapped_column(ForeignKey("ementas.id", ondelete="CASCADE"), index=True)
    ordem: Mapped[int]
    nome: Mapped[str] = mapped_column(String(200))
    periodo: Mapped[int | None]
    carga_horaria: Mapped[int | None]

    ementa: Mapped[Ementa] = relationship(back_populates="disciplinas")
    assuntos: Mapped[list["AssuntoEmenta"]] = relationship(
        back_populates="disciplina", cascade="all, delete-orphan", order_by="AssuntoEmenta.ordem"
    )


class AssuntoEmenta(Base):
    """Um assunto do conteúdo programático e onde ele está no catálogo.

    Coberto, aponta para o módulo; senão, para a lacuna. Nunca para os dois.
    """

    __tablename__ = "ementa_assuntos"
    __table_args__ = (
        UniqueConstraint("disciplina_id", "ordem", name="uq_ementa_assuntos_disciplina_ordem"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    disciplina_id: Mapped[int] = mapped_column(
        ForeignKey("ementa_disciplinas.id", ondelete="CASCADE"), index=True
    )
    ordem: Mapped[int]
    texto: Mapped[str] = mapped_column(String(300))
    # Apagar o módulo não apaga o assunto: ele só deixa de estar coberto.
    modulo_id: Mapped[int | None] = mapped_column(
        ForeignKey("modulos.id", ondelete="SET NULL"), index=True
    )
    lacuna_id: Mapped[int | None] = mapped_column(
        ForeignKey("lacunas.id", ondelete="SET NULL"), index=True
    )
    # Distância de cosseno até o módulo mais próximo no vault, coberto ou não.
    # É o que se olha para calibrar `ementa_distancia_maxima`.
    distancia: Mapped[float | None]

    disciplina: Mapped[DisciplinaEmenta] = relationship(back_populates="assuntos")
    modulo: Mapped["Modulo | None"] = relationship()
    lacuna: Mapped["Lacuna | None"] = relationship()


class Lacuna(Base, TimestampMixin):
    """Assunto que nenhum módulo cobre, um só para todas as ementas que o pedem.

    Dois alunos com "Recursão" em Algoritmos geram uma lacuna, e a busca de
    conteúdo (#207) roda uma vez. A `chave` é a disciplina e o assunto
    normalizados (sem acento, caixa e espaços extras).
    """

    __tablename__ = "lacunas"

    id: Mapped[int] = mapped_column(primary_key=True)
    chave: Mapped[str] = mapped_column(String(520), unique=True)
    disciplina: Mapped[str] = mapped_column(String(200))
    assunto: Mapped[str] = mapped_column(String(300))
    status: Mapped[StatusLacuna] = mapped_column(default=StatusLacuna.pendente, index=True)
