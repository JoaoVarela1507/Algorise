"""O painel de gamificação do aluno e o teto de XP por janela (telas 16 e 20).

Junta o que já existia espalhado — XP, níveis e streak — na resposta única que
as telas pedem, e acrescenta a proteção contra farm que faltava.

Sobre o teto: desde a #30 o XP sai **uma vez por atividade**, o que já impede
repetir a mesma para pontuar. O que ele impede é o outro caminho — um script
varrendo o catálogo inteiro numa tarde. O contador vive no Redis, numa janela
fixa, como o rate limit das rotas.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from redis import Redis
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.cache import chave
from app.core.config import settings
from app.core.redis import executar
from app.models import RespostaUsuario, Usuario, XPEvento
from app.services import niveis, streak


@dataclass(frozen=True)
class Painel:
    """O que as telas 16 e 20 mostram sobre o progresso do aluno."""

    xp_total: int
    nivel: int
    xp_no_nivel: int
    xp_para_o_proximo: int
    streak_dias: int
    maior_streak: int


def painel(db: Session, usuario: Usuario) -> Painel:
    """Monta o painel sem efeito nenhum: só leitura.

    O streak é lido, não registrado — quem registra é o check-in. Uma tela que
    só exibe não deveria mexer na sequência do aluno.
    """
    atual = streak.obter_streak(db, usuario.id)
    nivel, no_nivel, para_o_proximo = niveis.faixa_do_nivel(usuario.xp_total)

    return Painel(
        xp_total=usuario.xp_total,
        nivel=nivel,
        xp_no_nivel=no_nivel,
        xp_para_o_proximo=para_o_proximo,
        streak_dias=atual.dias_consecutivos,
        maior_streak=atual.maior_sequencia,
    )


def checkin(db: Session, usuario: Usuario) -> Painel:
    """Registra o acesso do dia e devolve o painel já atualizado.

    Chamar várias vezes no mesmo dia é seguro: o `registrar_acesso` conta uma
    vez por dia de calendário (ver `services/streak.py`).
    """
    streak.registrar_acesso(db, usuario.id)
    return painel(db, usuario)


@dataclass(frozen=True)
class MetaDiaria:
    """O anel de "meta diária" da tela 16: o que o aluno fez hoje."""

    xp_hoje: int
    xp_meta: int
    desafios_resolvidos: int
    minutos_estudados: int


def meta_diaria(db: Session, usuario: Usuario) -> MetaDiaria:
    """XP, desafios e minutos de hoje, no fuso do aluno.

    O dia é o mesmo do streak (`FUSO_HORARIO`): quem estuda às 23h no Recife
    ainda está no dia de hoje, mesmo que em UTC já seja amanhã.
    """
    inicio, fim = janela_do_dia()

    xp_hoje = db.scalar(
        select(func.coalesce(func.sum(XPEvento.valor), 0)).where(
            XPEvento.usuario_id == usuario.id,
            XPEvento.criado_em >= inicio,
            XPEvento.criado_em < fim,
        )
    )
    do_dia = (
        RespostaUsuario.usuario_id == usuario.id,
        RespostaUsuario.criado_em >= inicio,
        RespostaUsuario.criado_em < fim,
    )
    # Desafio resolvido é atividade acertada: errar três vezes e acertar na
    # quarta conta um, não quatro.
    desafios = db.scalar(
        select(func.count(func.distinct(RespostaUsuario.atividade_id))).where(
            *do_dia, RespostaUsuario.correta.is_(True)
        )
    )
    segundos = db.scalar(
        select(func.coalesce(func.sum(RespostaUsuario.tempo_gasto_segundos), 0)).where(*do_dia)
    )

    return MetaDiaria(
        xp_hoje=int(xp_hoje or 0),
        xp_meta=settings.xp_meta_diaria,
        desafios_resolvidos=int(desafios or 0),
        minutos_estudados=int(segundos or 0) // 60,
    )


def janela_do_dia(agora: datetime | None = None) -> tuple[datetime, datetime]:
    """Meia-noite de hoje e de amanhã no fuso do aluno, em UTC, para filtrar no banco."""
    fuso = ZoneInfo(settings.fuso_horario)
    dia = (agora or datetime.now(fuso)).astimezone(fuso).date()
    inicio = datetime.combine(dia, time.min, tzinfo=fuso)
    return inicio.astimezone(UTC), (inicio + timedelta(days=1)).astimezone(UTC)


def xp_permitido(usuario_id: int, valor: int) -> int:
    """Quanto desse XP cabe no teto da janela. Zero quando já estourou.

    Devolve um número, e não um sim/não, para o último ganho da janela não ser
    perdido inteiro: quem está a 5 XP do teto recebe esses 5.

    **Com o Redis fora, libera tudo.** O teto existe contra abuso, e derrubar a
    concessão de XP por causa do cache puniria o aluno honesto — a mesma escolha
    do rate limit (#12).
    """
    if valor <= 0:
        return 0

    nome = chave("xp", "janela", usuario_id)
    teto = settings.xp_maximo_por_janela

    def contar(r: Redis) -> int:
        with r.pipeline() as pipe:
            pipe.incrby(nome, valor)
            # `nx`: só a primeira concessão da janela define o vencimento, senão
            # a janela nunca viraria.
            pipe.expire(nome, settings.xp_janela_segundos, nx=True)
            acumulado, *_ = pipe.execute()
        return int(acumulado)

    acumulado = executar(contar, padrao=None)
    if acumulado is None:
        return valor

    excedente = acumulado - teto
    if excedente <= 0:
        return valor

    # Devolve o que passou do teto para o contador não inflar sozinho e manter a
    # janela coerente com o que foi realmente concedido.
    cabe = max(valor - excedente, 0)
    executar(lambda r: r.decrby(nome, valor - cabe))
    return cabe
