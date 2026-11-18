"""Testa o provedor de IA configurado, sem subir a API nem o banco.

    python scripts/testar_ia.py                       # usa o IA_PROVEDOR do .env
    python scripts/testar_ia.py gemini                # força o Gemini
    python scripts/testar_ia.py ollama "O que é um for?"

Manda uma pergunta ao modelo do chat, mostra a resposta chegando em pedaços e o
tempo, pede um JSON no formato de uma skill e confere o embedding (a dimensão
que o vault exige). Serve para comparar o Ollama e o Gemini lado a lado.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Roda de dentro de `backend/`, como a API: o `.env` e o pacote `app` estão aqui.
_BACKEND = Path(__file__).resolve().parent.parent
os.chdir(_BACKEND)
sys.path.insert(0, str(_BACKEND))
# O console do Windows não é UTF-8 por padrão: sem isso, os acentos saem trocados.
sys.stdout.reconfigure(encoding="utf-8")

from app.core.config import settings  # noqa: E402
from app.ia import IAIndisponivel, MensagemIA, get_provedor_ia, get_provedor_ia_tarefas  # noqa: E402

PERGUNTA_PADRAO = "Explique em duas frases o que é um laço for em Python."

FORMATO = {
    "type": "object",
    "properties": {
        "assuntos": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["assuntos"],
}


async def testar(pergunta: str) -> int:
    chat = get_provedor_ia()
    tarefas = get_provedor_ia_tarefas()
    print(f"Provedor: {settings.ia_provedor}")
    print(f"Modelo do chat: {getattr(chat, 'modelo', '-')}")
    print(f"Modelo das tarefas: {getattr(tarefas, 'modelo', '-')}\n")

    try:
        print(f"> {pergunta}")
        inicio = time.perf_counter()
        primeiro = None
        async for pedaco in chat.gerar(
            [MensagemIA("system", "Você é um tutor de programação."), MensagemIA("user", pergunta)],
            max_tokens=300,
        ):
            primeiro = primeiro or time.perf_counter() - inicio
            print(pedaco, end="", flush=True)
        total = time.perf_counter() - inicio
        print(f"\n\n[chat] primeiro pedaço em {primeiro or 0:.1f}s, total {total:.1f}s")

        if settings.ia_provedor == "eco":
            return 0  # o eco só devolve a pergunta: não há JSON nem embedding para testar

        inicio = time.perf_counter()
        texto = "".join(
            [
                p
                async for p in tarefas.gerar(
                    [
                        MensagemIA(
                            "user",
                            "Liste os assuntos desta ementa: Variáveis, laços de repetição, "
                            "funções e listas em Python.",
                        )
                    ],
                    max_tokens=300,
                    formato=FORMATO,
                )
            ]
        )
        assuntos = json.loads(texto)["assuntos"]
        print(f"[tarefas/JSON] {assuntos} em {time.perf_counter() - inicio:.1f}s")

        inicio = time.perf_counter()
        vetores = await tarefas.embeddings(["laço for", "repetição em Python"])
        print(
            f"[embedding] {len(vetores)} vetores de {len(vetores[0])} dimensões "
            f"em {time.perf_counter() - inicio:.1f}s"
        )
    except IAIndisponivel as erro:
        print(f"\nIA indisponível: {erro}")
        return 1
    except (json.JSONDecodeError, KeyError) as erro:
        print(f"\nO modelo não devolveu o JSON pedido: {erro}")
        return 1
    return 0


def main() -> int:
    argumentos = sys.argv[1:]
    if argumentos and argumentos[0] in ("ollama", "gemini", "eco"):
        settings.ia_provedor = argumentos.pop(0)
    pergunta = " ".join(argumentos) or PERGUNTA_PADRAO
    return asyncio.run(testar(pergunta))


if __name__ == "__main__":
    sys.exit(main())
