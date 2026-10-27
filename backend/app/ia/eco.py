"""Provedor de teste, sem rede."""

import asyncio
from collections.abc import AsyncGenerator, Sequence

from app.ia.base import MensagemIA


class Eco:
    """Provedor de teste: devolve a última pergunta, em pedaços, sem rede.

    Serve ao E2E e a quem quer rodar o chat sem o Ollama. A resposta é
    previsível de propósito, para o teste saber o que esperar na tela.
    """

    async def gerar(
        self, mensagens: Sequence[MensagemIA], *, max_tokens: int
    ) -> AsyncGenerator[str]:
        pergunta = next((m.conteudo for m in reversed(mensagens) if m.papel == "user"), "")
        resposta = f"Você perguntou: {pergunta}"
        palavras = resposta.split(" ")[:max_tokens]
        for i, palavra in enumerate(palavras):
            yield palavra if i == 0 else f" {palavra}"
            # Cede a vez ao event loop, como um provedor de verdade faria entre
            # um pedaço e outro.
            await asyncio.sleep(0)
