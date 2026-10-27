"""Provedor de teste, sem rede."""

import asyncio
import hashlib
import math
import re
import unicodedata
from collections.abc import AsyncGenerator, Sequence
from typing import Any

from app.ia.base import DIMENSOES_EMBEDDING, MensagemIA


class Eco:
    """Provedor de teste: devolve a última pergunta, em pedaços, sem rede.

    Serve ao E2E e a quem quer rodar o chat sem o Ollama. A resposta é
    previsível de propósito, para o teste saber o que esperar na tela.
    """

    async def gerar(
        self,
        mensagens: Sequence[MensagemIA],
        *,
        max_tokens: int,
        formato: dict[str, Any] | None = None,
    ) -> AsyncGenerator[str]:
        pergunta = next((m.conteudo for m in reversed(mensagens) if m.papel == "user"), "")
        resposta = f"Você perguntou: {pergunta}"
        palavras = resposta.split(" ")[:max_tokens]
        for i, palavra in enumerate(palavras):
            yield palavra if i == 0 else f" {palavra}"
            # Cede a vez ao event loop, como um provedor de verdade faria entre
            # um pedaço e outro.
            await asyncio.sleep(0)

    async def embeddings(self, textos: Sequence[str]) -> list[list[float]]:
        return [vetor_de_palavras(texto) for texto in textos]


def vetor_de_palavras(texto: str) -> list[float]:
    """Embedding falso: cada palavra soma 1 numa posição sorteada pelo hash dela.

    Não entende sinônimo, mas textos com palavras em comum ficam próximos, e é
    isso que a busca do vault precisa para ser testada sem o modelo. O hash é o
    MD5, e não o `hash()`, para o vetor ser o mesmo em toda execução.
    """
    sem_acento = unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()
    vetor = [0.0] * DIMENSOES_EMBEDDING
    # Palavras curtas ("de", "o", "um") aparecem em tudo e só aproximariam
    # textos que não têm nada a ver.
    for palavra in re.findall(r"\w{3,}", sem_acento):
        resumo = hashlib.md5(palavra.encode(), usedforsecurity=False).digest()
        posicao = int.from_bytes(resumo[:4]) % DIMENSOES_EMBEDDING
        vetor[posicao] += 1.0
    norma = math.sqrt(sum(v * v for v in vetor)) or 1.0
    return [v / norma for v in vetor]
