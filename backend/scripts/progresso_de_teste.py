"""Deixa uma conta com trilhas concluídas e pela metade, para testar as telas.

Faz o que o aluno faria, pelas regras do app (`services/progresso` e
`services/submissoes`): começa a trilha, responde certo cada atividade, fecha o
passo. Assim XP, desbloqueio, ranking, conquistas e conclusão ficam coerentes
entre si, e não só uma linha marcada como "concluída" no banco.

    python scripts/progresso_de_teste.py --email aluno@example.com
    python scripts/progresso_de_teste.py --email aluno@example.com \\
        --concluir logica-de-programacao --metade estruturas-de-dados

Por padrão conclui a Lógica de Programação e faz metade dos passos de
Estruturas de Dados (as trilhas de `app/seeds/trilhas_extras.py`).

Só para desenvolvimento: dentro deste processo o teto de XP por hora (o
anti-farm, #31) fica de lado, senão a segunda trilha não pagaria XP nenhum.
Rodar de novo não repete o que já está feito.

Com `--streak N`, o histórico vira N dias seguidos de estudo terminando hoje:
as respostas e o XP da conta são espalhados por esses dias, na ordem em que
aconteceram, e o streak passa a N. Assim a meta diária (que soma só o de hoje),
o ranking da semana e o "dias seguidos" contam a mesma história.
"""

import argparse
import os
import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# Roda de dentro de `backend/`, como a API: o `.env` e o pacote `app` estão aqui.
_BACKEND = Path(__file__).resolve().parent.parent
os.chdir(_BACKEND)
sys.path.insert(0, str(_BACKEND))
sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Modulo,
    ProgressoUsuario,
    RespostaUsuario,
    Trilha,
    Usuario,
    XPEvento,
)
from app.models.enums import OrigemXP, TipoAtividade  # noqa: E402
from app.services import progresso, submissoes  # noqa: E402
from app.services import streak as streak_servico  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--email", required=True, help="a conta que recebe o progresso")
    parser.add_argument("--concluir", default=["logica-de-programacao"], nargs="*")
    parser.add_argument("--metade", default=["estruturas-de-dados"], nargs="*")
    parser.add_argument("--streak", type=int, default=0, help="dias seguidos, terminando hoje")
    args = parser.parse_args()

    settings.xp_maximo_por_janela = 10**9
    with SessionLocal() as db:
        usuario = db.scalar(select(Usuario).where(Usuario.email == args.email))
        if usuario is None:
            print(f"erro: nenhuma conta com o e-mail {args.email}", file=sys.stderr)
            return 1
        xp_antes = usuario.xp_total
        plano = [(slug, 1.0) for slug in args.concluir] + [(slug, 0.5) for slug in args.metade]
        for slug, fracao in plano:
            trilha = db.scalar(select(Trilha).where(Trilha.slug == slug))
            if trilha is None:
                print(f"erro: trilha {slug} não existe (rode `python -m app.seeds`)")
                return 1
            modulos = sorted(trilha.modulos, key=lambda m: m.ordem)
            quantos = round(len(modulos) * fracao)
            progresso.iniciar_trilha(db, usuario_id=usuario.id, trilha=trilha)
            for modulo in modulos[:quantos]:
                _fazer_passo(db, usuario, trilha, modulo)
            print(f"{trilha.nome}: {quantos} de {len(modulos)} passos concluídos")
        db.refresh(usuario)
        print(f"XP de {usuario.username}: {xp_antes} -> {usuario.xp_total}")
        if args.streak > 0:
            _espalhar_em_dias_seguidos(db, usuario, args.streak)
    return 0


def _espalhar_em_dias_seguidos(db: Session, usuario: Usuario, dias: int) -> None:
    """Redistribui respostas e XP pelos últimos `dias` dias e acerta o streak."""
    hoje = streak_servico.hoje_no_fuso()
    fuso = ZoneInfo(settings.fuso_horario)
    respostas = db.scalars(
        select(RespostaUsuario).where(RespostaUsuario.usuario_id == usuario.id)
    ).all()
    eventos = db.scalars(select(XPEvento).where(XPEvento.usuario_id == usuario.id)).all()
    # Respostas e XP juntos, na ordem em que aconteceram: o XP de uma atividade
    # continua logo depois da resposta que o gerou, e o do passo depois dele.
    linha_do_tempo = sorted([*respostas, *eventos], key=lambda item: (item.criado_em, item.id))
    total = len(linha_do_tempo)
    novos: dict[int, datetime] = {}
    for indice, item in enumerate(linha_do_tempo):
        dia = hoje - timedelta(days=dias - 1 - indice * dias // max(total, 1))
        # Uma sessão de estudo à noite, um minuto por item.
        quando = datetime.combine(dia, time(19, 0), tzinfo=fuso) + timedelta(minutes=indice % 50)
        item.criado_em = quando
        if isinstance(item, XPEvento) and item.origem is OrigemXP.modulo and item.referencia_id:
            novos[item.referencia_id] = quando

    for registro in db.scalars(
        select(ProgressoUsuario).where(ProgressoUsuario.usuario_id == usuario.id)
    ):
        if registro.modulo_id in novos:
            registro.concluido_em = novos[registro.modulo_id]

    # A linha gravada (o `obter_streak` só lê, e devolve uma cópia para exibir).
    streak = streak_servico.registrar_acesso(db, usuario.id, hoje=hoje)
    streak.dias_consecutivos = dias
    streak.maior_sequencia = max(streak.maior_sequencia, dias)
    streak.ultimo_acesso = hoje
    db.commit()
    print(f"{total} respostas e eventos de XP espalhados em {dias} dias; streak = {dias}")


def _fazer_passo(db: Session, usuario: Usuario, trilha: Trilha, modulo: Modulo) -> None:
    if progresso.esta_concluido(db, usuario_id=usuario.id, modulo_id=modulo.id):
        return
    for atividade in modulo.atividades:
        if atividade.tipo not in submissoes.TIPOS_CORRIGIVEIS:
            continue  # o desafio de código precisa da sandbox, e não fecha o passo
        ja_respondeu = db.scalar(
            select(RespostaUsuario.id).where(
                RespostaUsuario.usuario_id == usuario.id,
                RespostaUsuario.atividade_id == atividade.id,
            )
        )
        if ja_respondeu:
            continue
        resposta = (
            atividade.comando_esperado
            if atividade.tipo is TipoAtividade.terminal
            else atividade.resposta_esperada
        )
        submissoes.submeter(
            db,
            usuario=usuario,
            atividade=atividade,
            conteudo=resposta or "",
            tempo_gasto_segundos=atividade.tempo_sugerido_segundos,
        )
    submissoes.concluir_passo(db, usuario=usuario, trilha=trilha, modulo=modulo)


if __name__ == "__main__":
    sys.exit(main())
