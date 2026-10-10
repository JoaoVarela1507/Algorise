"""Concessão de XP: grava o evento, atualiza o saldo e corrige o ranking.

O único caminho por onde o XP deve entrar. Quem chamar isso não precisa saber que
existe um sorted set no Redis — é aqui que a invalidação do ranking acontece.
"""

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import OrigemXP, Usuario, XPEvento
from app.services import gamificacao, ranking


def registrar_xp(
    db: Session,
    *,
    usuario_id: int,
    valor: int,
    origem: OrigemXP,
    referencia_id: int | None = None,
) -> int:
    """Concede `valor` de XP ao aluno e devolve o novo saldo.

    O valor passa pelo teto por janela (#31) antes de entrar: o que exceder é
    descartado, e o resto é concedido normalmente. Devolver só o saldo mantém
    quem chama livre de saber disso.

    O evento em `xp_eventos` é a fonte da verdade; `usuarios.xp_total` é o saldo
    desnormalizado. O `UPDATE ... SET xp_total = xp_total + valor` soma no banco
    em vez de em Python, para dois pedidos simultâneos não sobrescreverem um ao
    outro.
    """
    valor = gamificacao.xp_permitido(usuario_id, valor)
    if valor <= 0:
        # Estourou o teto: o progresso continua gravado (a atividade está feita),
        # só não vira ponto.
        return db.execute(select(Usuario.xp_total).where(Usuario.id == usuario_id)).scalar_one()

    db.add(
        XPEvento(
            usuario_id=usuario_id,
            origem=origem,
            referencia_id=referencia_id,
            valor=valor,
        )
    )
    db.execute(
        update(Usuario).where(Usuario.id == usuario_id).values(xp_total=Usuario.xp_total + valor)
    )
    db.commit()

    # Depois do commit, nunca antes: se a transação falhar, o ranking não pode
    # ficar com um XP que o banco não tem.
    ranking.registrar_xp(usuario_id, valor)

    return db.execute(select(Usuario.xp_total).where(Usuario.id == usuario_id)).scalar_one()
