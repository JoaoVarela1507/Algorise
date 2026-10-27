"""O painel de gamificação do aluno e o teto de XP por janela (telas 16 e 20).

Junta o que já existia espalhado — XP, níveis e streak — na resposta única que
as telas pedem, e acrescenta a proteção contra farm que faltava.

Sobre o teto: desde a #30 o XP sai **uma vez por atividade**, o que já impede
repetir a mesma para pontuar. O que ele impede é o outro caminho — um script
varrendo o catálogo inteiro numa tarde. O contador vive no Redis, numa janela
fixa, como o rate limit das rotas.
"""

from dataclasses import dataclass

from redis import Redis
from sqlalchemy.orm import Session

from app.core.cache import chave
from app.core.config import settings
from app.core.redis import executar
from app.models import Usuario
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
