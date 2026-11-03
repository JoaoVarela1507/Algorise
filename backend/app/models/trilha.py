"""Catálogo: trilha, seus módulos e as atividades de cada módulo."""

from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import NivelExperiencia, OrigemModulo, StatusGeracao, TipoAtividade

if TYPE_CHECKING:
    from app.models.gamificacao import Parceiro
    from app.models.youtube import ParteVideo


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
    # Certificado (#32): só a trilha de parceiro emite, e a carga horária, em
    # horas, vai no certificado.
    parceiro_id: Mapped[int | None] = mapped_column(
        ForeignKey("parceiros.id", ondelete="SET NULL"), index=True
    )
    carga_horaria: Mapped[int | None]

    parceiro: Mapped["Parceiro | None"] = relationship()
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
    # O trecho do vídeo que o player toca (`?start=&end=`): o módulo que é uma
    # parte de uma aula longa (#210). Sem eles, o vídeo inteiro.
    inicio_segundos: Mapped[float | None]
    fim_segundos: Mapped[float | None]
    origem: Mapped[OrigemModulo] = mapped_column(
        default=OrigemModulo.manual, server_default=OrigemModulo.manual.value
    )
    # A parte de vídeo de onde o módulo automático saiu. Uma parte vira no
    # máximo um módulo: é o que impede duplicar ao publicar de novo.
    parte_video_id: Mapped[int | None] = mapped_column(
        ForeignKey("partes_video.id", ondelete="SET NULL"), unique=True
    )

    trilha: Mapped[Trilha] = relationship(back_populates="modulos")
    parte_video: Mapped["ParteVideo | None"] = relationship()
    atividades: Mapped[list["Atividade"]] = relationship(
        back_populates="modulo", cascade="all, delete-orphan", order_by="Atividade.ordem"
    )

    @property
    def canal(self) -> str | None:
        """O canal do YouTube do vídeo, no módulo automático."""
        return self.parte_video.video.canal if self.parte_video else None


class ReporteModulo(Base, TimestampMixin):
    """Um aluno disse que o vídeo do módulo automático não serve (#210).

    Um por aluno e módulo: reportar de novo não conta duas vezes.
    """

    __tablename__ = "reportes_modulo"
    __table_args__ = (
        UniqueConstraint("modulo_id", "usuario_id", name="uq_reportes_modulo_modulo_usuario"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    modulo_id: Mapped[int] = mapped_column(ForeignKey("modulos.id", ondelete="CASCADE"), index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))


class ExerciciosGerados(Base, TimestampMixin):
    """Os exercícios de prática de um módulo para um nível, gerados pela IA (#201).

    Um por módulo e nível: gerado uma vez, na fila, e servido a todos os
    alunos daquele nível. Não conta para concluir o passo.
    """

    __tablename__ = "exercicios_gerados"
    __table_args__ = (
        UniqueConstraint("modulo_id", "nivel", name="uq_exercicios_gerados_modulo_nivel"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    modulo_id: Mapped[int] = mapped_column(ForeignKey("modulos.id", ondelete="CASCADE"), index=True)
    nivel: Mapped[NivelExperiencia]
    status: Mapped[StatusGeracao] = mapped_column(default=StatusGeracao.gerando)
    # Lista de {enunciado, resposta_esperada, dica}, validada pela skill.
    exercicios: Mapped[list[dict]] = mapped_column(JSON, default=list)
    erro: Mapped[str | None] = mapped_column(Text)


class Atividade(Base, TimestampMixin):
    __tablename__ = "atividades"
    __table_args__ = (UniqueConstraint("modulo_id", "ordem", name="uq_atividades_modulo_ordem"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    modulo_id: Mapped[int] = mapped_column(ForeignKey("modulos.id", ondelete="CASCADE"), index=True)
    ordem: Mapped[int]
    tipo: Mapped[TipoAtividade]
    enunciado: Mapped[str] = mapped_column(Text)
    dica: Mapped[str | None] = mapped_column(Text)

    # O que a tela mostra além do enunciado, conforme o tipo. É público: vai
    # para o cliente junto com o enunciado.
    # - múltipla escolha: as alternativas;
    # - ordenação: os itens, já embaralhados (a ordem gravada é a da tela);
    # - lacuna: o banco de palavras, opcional.
    opcoes: Mapped[list[str] | None] = mapped_column(JSON)
    # Trecho de código mostrado na atividade. Na lacuna, cada `___` é um buraco.
    codigo: Mapped[str | None] = mapped_column(Text)

    # Gabarito. Nunca deve ser serializado para o cliente antes da submissão
    # (ver #30).
    comando_esperado: Mapped[str | None] = mapped_column(String(500))
    saida_esperada: Mapped[str | None] = mapped_column(Text)
    # Múltipla escolha: o texto da alternativa certa. Ordenação e lacuna: uma
    # lista JSON (os itens na ordem certa; a resposta de cada buraco).
    resposta_esperada: Mapped[str | None] = mapped_column(Text)

    tempo_sugerido_segundos: Mapped[int | None]
    xp: Mapped[int] = mapped_column(default=10)

    modulo: Mapped[Modulo] = relationship(back_populates="atividades")
