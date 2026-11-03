"""Desafio de código (#34): os casos de teste e as execuções na sandbox."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import StatusExecucao


class CasoDeTeste(Base, TimestampMixin):
    """Entrada no stdin e a saída esperada no stdout.

    O público aparece na tela com entrada e saída; o oculto só diz se passou,
    para o aluno não escrever um `if` para cada caso.
    """

    __tablename__ = "casos_de_teste"

    id: Mapped[int] = mapped_column(primary_key=True)
    atividade_id: Mapped[int] = mapped_column(
        ForeignKey("atividades.id", ondelete="CASCADE"), index=True
    )
    ordem: Mapped[int]
    entrada: Mapped[str] = mapped_column(Text, default="")
    saida_esperada: Mapped[str] = mapped_column(Text)
    publico: Mapped[bool] = mapped_column(default=True, server_default=false())


class Execucao(Base, TimestampMixin):
    """Uma tentativa do aluno, rodada no worker. O id é o do job da fila."""

    __tablename__ = "execucoes"
    __table_args__ = (Index("ix_execucoes_usuario_atividade", "usuario_id", "atividade_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    atividade_id: Mapped[int] = mapped_column(ForeignKey("atividades.id", ondelete="CASCADE"))
    codigo: Mapped[str] = mapped_column(Text)
    status: Mapped[StatusExecucao] = mapped_column(default=StatusExecucao.na_fila)
    # A saída do primeiro caso que falhou (ou do último, se todos passaram).
    stdout: Mapped[str] = mapped_column(Text, default="")
    stderr: Mapped[str] = mapped_column(Text, default="")
    # Um item por caso: `ordem`, `publico`, `passou` e, nos públicos, o que saiu.
    casos: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    aprovada: Mapped[bool] = mapped_column(default=False, server_default=false())
    erro: Mapped[str | None] = mapped_column(String(300))
    terminada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
