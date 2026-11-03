"""Muda o papel de um usuário: autor de conteúdo ou admin (#41).

Não há rota para isso de propósito: dar poder a alguém pela própria API abriria
a porta para quem conseguir um token de admin dar poder a qualquer um. Quem tem
acesso ao servidor roda, da pasta `backend/`:

    python -m app.tarefas.papeis ana@ufrpe.br admin
"""

import argparse
import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import PapelUsuario, Usuario


def main(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.tarefas.papeis")
    parser.add_argument("email")
    parser.add_argument("papel", choices=[papel.value for papel in PapelUsuario])
    args = parser.parse_args(argumentos)

    with SessionLocal() as db:
        usuario = db.scalar(select(Usuario).where(Usuario.email == args.email.strip().lower()))
        if usuario is None:
            print(f"erro: nenhum usuário com o e-mail {args.email}", file=sys.stderr)
            return 1
        usuario.papel = PapelUsuario(args.papel)
        db.commit()
    print(f"{args.email}: {args.papel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
