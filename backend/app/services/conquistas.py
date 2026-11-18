"""Conquistas do aluno, o card de medalhas da home (tela 16).

Nada aqui é gravado: cada conquista é uma pergunta sobre o que já está no banco
(respostas, streak, XP, progresso). Assim uma regra nova vale para o histórico
inteiro, sem migração nem rotina para "desbloquear o que já devia estar".

O `id` é o contrato com o frontend, que escolhe o ícone por ele; título e
descrição vêm daqui para o texto morar num lugar só.

As perguntas sobre o histórico de respostas (primeiro acerto, coruja,
maratonista) são agregadas no banco: trazer todas as respostas do aluno para o
Python crescia com o uso, e quem mais usa é quem mais abre a home. O horário
local sai do `timezone()` do PostgreSQL. O SQLite (suíte e E2E) não tem fuso,
então lá a conta continua no Python, com o mesmo resultado.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import Date, Select, cast, exists, extract, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Modulo, ProgressoUsuario, RespostaUsuario, StatusProgresso, Usuario
from app.services import ranking, streak

# "Depois da meia-noite" é madrugada: até as 5h ainda é coisa de coruja.
HORA_FIM_DA_MADRUGADA = 5
DIAS_EM_CHAMAS = 3
MINUTOS_MARATONA = 60
POSICAO_TOP = 10


@dataclass(frozen=True)
class Conquista:
    id: str
    titulo: str
    descricao: str
    desbloqueada: bool


def conquistas(db: Session, usuario: Usuario) -> list[Conquista]:
    """Todas as conquistas, na ordem do card, cada uma dizendo se já saiu."""
    no_postgres = db.get_bind().dialect.name == "postgresql"
    sequencia = streak.obter_streak(db, usuario.id)

    return [
        Conquista(
            id="primeiro-passo",
            titulo="Primeiro passo",
            descricao="Resolveu o primeiro desafio.",
            desbloqueada=_resolveu_algum(db, usuario.id),
        ),
        Conquista(
            id="em-chamas",
            titulo="Em chamas",
            descricao=f"Estudou {DIAS_EM_CHAMAS} dias seguidos.",
            desbloqueada=sequencia.maior_sequencia >= DIAS_EM_CHAMAS,
        ),
        Conquista(
            id="top-10",
            titulo="Top 10",
            descricao=f"Entrou no top {POSICAO_TOP} do ranking geral.",
            desbloqueada=_no_top(db, usuario),
        ),
        Conquista(
            id="coruja",
            titulo="Coruja",
            descricao="Resolveu um desafio depois da meia-noite.",
            desbloqueada=_resolveu_de_madrugada(db, usuario.id, no_postgres=no_postgres),
        ),
        Conquista(
            id="maratonista",
            titulo="Maratonista",
            descricao=f"Estudou {MINUTOS_MARATONA} minutos em um único dia.",
            desbloqueada=(
                _maior_dia_em_minutos(db, usuario.id, no_postgres=no_postgres) >= MINUTOS_MARATONA
            ),
        ),
        Conquista(
            id="trilha-completa",
            titulo="Trilha completa",
            descricao="Concluiu todos os módulos de uma trilha.",
            desbloqueada=_concluiu_alguma_trilha(db, usuario.id),
        ),
    ]


def _no_local(quando: datetime) -> datetime:
    """O horário no fuso do aluno. O SQLite devolve sem fuso, e aí ele é UTC."""
    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=UTC)
    return quando.astimezone(ZoneInfo(settings.fuso_horario))


def _acertos(usuario_id: int) -> tuple:
    return (RespostaUsuario.usuario_id == usuario_id, RespostaUsuario.correta.is_(True))


def _resolveu_algum(db: Session, usuario_id: int) -> bool:
    return bool(db.scalar(select(exists().where(*_acertos(usuario_id)))))


def _horario_local():
    """`criado_em` no fuso do aluno, como horário sem fuso (só no PostgreSQL)."""
    return func.timezone(settings.fuso_horario, RespostaUsuario.criado_em)


def consulta_de_madrugada(usuario_id: int) -> Select:
    """Algum acerto entre meia-noite e `HORA_FIM_DA_MADRUGADA`, no fuso do aluno."""
    return select(
        exists().where(
            *_acertos(usuario_id), extract("hour", _horario_local()) < HORA_FIM_DA_MADRUGADA
        )
    )


def consulta_do_maior_dia(usuario_id: int) -> Select:
    """Os segundos do dia (no fuso do aluno) com mais tempo gasto nas atividades."""
    por_dia = (
        select(func.sum(RespostaUsuario.tempo_gasto_segundos).label("segundos"))
        .where(
            RespostaUsuario.usuario_id == usuario_id,
            RespostaUsuario.tempo_gasto_segundos.is_not(None),
        )
        .group_by(cast(_horario_local(), Date))
        .subquery()
    )
    return select(func.coalesce(func.max(por_dia.c.segundos), 0))


def _resolveu_de_madrugada(db: Session, usuario_id: int, *, no_postgres: bool) -> bool:
    if no_postgres:
        return bool(db.scalar(consulta_de_madrugada(usuario_id)))

    horarios = db.scalars(select(RespostaUsuario.criado_em).where(*_acertos(usuario_id)))
    return any(_no_local(quando).hour < HORA_FIM_DA_MADRUGADA for quando in horarios)


def _maior_dia_em_minutos(db: Session, usuario_id: int, *, no_postgres: bool) -> int:
    """O dia (no fuso do aluno) com mais tempo gasto nas atividades, em minutos."""
    if no_postgres:
        return int(db.scalar(consulta_do_maior_dia(usuario_id)) or 0) // 60

    linhas = db.execute(
        select(RespostaUsuario.criado_em, RespostaUsuario.tempo_gasto_segundos).where(
            RespostaUsuario.usuario_id == usuario_id,
            RespostaUsuario.tempo_gasto_segundos.is_not(None),
        )
    ).all()

    por_dia: defaultdict[date, int] = defaultdict(int)
    for quando, segundos in linhas:
        por_dia[_no_local(quando).date()] += segundos
    return max(por_dia.values(), default=0) // 60


def _no_top(db: Session, usuario: Usuario) -> bool:
    # Sem XP não é top de nada, mesmo que a turma inteira também esteja zerada.
    if usuario.xp_total <= 0:
        return False
    entrada = ranking.posicao_geral(db, usuario.id)
    return entrada is not None and entrada.posicao <= POSICAO_TOP


def _concluiu_alguma_trilha(db: Session, usuario_id: int) -> bool:
    concluidos = (
        select(ProgressoUsuario.trilha_id, func.count(ProgressoUsuario.id).label("feitos"))
        .where(
            ProgressoUsuario.usuario_id == usuario_id,
            ProgressoUsuario.status == StatusProgresso.concluido,
        )
        .group_by(ProgressoUsuario.trilha_id)
        .subquery()
    )
    totais = (
        select(Modulo.trilha_id, func.count(Modulo.id).label("total"))
        .group_by(Modulo.trilha_id)
        .subquery()
    )
    completa = db.scalar(
        select(concluidos.c.trilha_id)
        .join(totais, totais.c.trilha_id == concluidos.c.trilha_id)
        .where(concluidos.c.feitos >= totais.c.total)
        .limit(1)
    )
    return completa is not None
