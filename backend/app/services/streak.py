"""Streak de dias consecutivos de acesso (tela 16).

A contagem mora no PostgreSQL, porque é histórico do aluno. O Redis entra para
não escrever no banco a cada request: um marcador diário registra que o acesso de
hoje já foi contabilizado, e aí os outros requests do mesmo dia só leem.

O marcador expira à meia-noite em vez de em 24 horas: o streak é por dia de
calendário, então o que interessa é a virada do dia, não o intervalo desde o
último acesso.

Sem Redis a conta é a mesma, só passa no banco toda vez — e o `UPDATE` continua
idempotente dentro do dia, porque a decisão vem de `ultimo_acesso`.
"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import chave
from app.core.redis import executar
from app.models import Streak


def registrar_acesso(db: Session, usuario_id: int, *, hoje: date | None = None) -> Streak:
    """Conta o acesso de hoje e devolve o streak atualizado.

    Chamar várias vezes no mesmo dia é seguro: a partir da segunda, com o Redis
    de pé, nem chega ao `UPDATE`.
    """
    hoje = hoje or date.today()
    marcador = chave("streak", "visto", usuario_id, hoje.isoformat())

    if executar(lambda r: r.exists(marcador), padrao=0):
        return _obter_ou_criar(db, usuario_id, hoje)

    streak = _atualizar(db, usuario_id, hoje)
    executar(lambda r: r.setex(marcador, _segundos_ate_amanha(hoje), "1"))
    return streak


def obter_streak(db: Session, usuario_id: int, *, hoje: date | None = None) -> Streak:
    """Streak para exibir, sem contar acesso.

    Zera na leitura quando o último acesso não foi hoje nem ontem: a sequência
    quebrou de fato, e mostrar o número velho seria mentir para o aluno.
    """
    hoje = hoje or date.today()
    streak = _obter_ou_criar(db, usuario_id, hoje)

    if streak.ultimo_acesso is not None and streak.ultimo_acesso < hoje - timedelta(days=1):
        streak.dias_consecutivos = 0
        db.commit()

    return streak


def _atualizar(db: Session, usuario_id: int, hoje: date) -> Streak:
    streak = _obter_ou_criar(db, usuario_id, hoje)

    if streak.ultimo_acesso == hoje:
        # Primeiro acesso do dia para o Redis, mas o banco já sabia: aconteceu
        # com o Redis fora, ou o marcador foi perdido.
        return streak

    if streak.ultimo_acesso == hoje - timedelta(days=1):
        streak.dias_consecutivos += 1
    else:
        # Buraco na sequência (ou primeiro acesso de todos): hoje conta como 1.
        streak.dias_consecutivos = 1

    streak.ultimo_acesso = hoje
    streak.maior_sequencia = max(streak.maior_sequencia, streak.dias_consecutivos)
    db.commit()
    return streak


def _obter_ou_criar(db: Session, usuario_id: int, hoje: date) -> Streak:
    streak = db.execute(select(Streak).where(Streak.usuario_id == usuario_id)).scalar_one_or_none()
    if streak is not None:
        return streak

    streak = Streak(usuario_id=usuario_id, dias_consecutivos=0, maior_sequencia=0)
    db.add(streak)
    db.commit()
    return streak


def _segundos_ate_amanha(hoje: date) -> int:
    """Quanto falta para a virada do dia, com no mínimo 1 segundo (o SETEX recusa 0)."""
    virada = datetime.combine(hoje + timedelta(days=1), time.min)
    return max(int((virada - datetime.now()).total_seconds()), 1)
