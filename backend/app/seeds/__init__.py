"""Seeds de conteúdo.

Rode da pasta `backend/`:

    python -m app.seeds
"""

from app.core.database import SessionLocal
from app.seeds import introducao_python


def main() -> None:
    with SessionLocal() as db:
        trilha = introducao_python.aplicar(db)
        # A coleção pode ter sido carregada vazia antes da inserção; recarrega
        # para o total impresso ser o que está no banco.
        db.refresh(trilha)
        print(f"seed aplicado: {trilha.nome} ({len(trilha.modulos)} módulos)")


if __name__ == "__main__":
    main()
