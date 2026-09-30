"""Escreve o OpenAPI num arquivo, sem subir o servidor.

Usado pelo `npm run gen:api`, que transforma esse arquivo nos tipos TypeScript do
frontend. Gerar direto do `app.openapi()` — em vez de dar `curl` num servidor
rodando — deixa o comando rodar em máquina limpa e no CI, sem banco nem Redis.

    python backend/scripts/exportar_openapi.py frontend/src/types/openapi.json
"""

import json
import sys
from pathlib import Path

# O script roda da raiz do repositório, então `app` ainda não está no path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app

PADRAO = Path("frontend/src/types/openapi.json")


def main() -> None:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else PADRAO
    destino.parent.mkdir(parents=True, exist_ok=True)

    # `sort_keys` e a quebra de linha no fim mantêm o arquivo estável entre
    # gerações: sem isso, cada execução viraria um diff gigante e inútil.
    conteudo = json.dumps(app.openapi(), indent=2, ensure_ascii=False, sort_keys=True)
    destino.write_text(conteudo + "\n", encoding="utf-8")

    print(f"OpenAPI escrito em {destino}")


if __name__ == "__main__":
    main()
