"""Contrato de todo provedor de IA: mensagens entram, pedaços de texto saem.

Quem usa a IA (o chat, a leitura da ementa, as skills que vierem) fala com
`ProvedorIA`, nunca com o Ollama direto: trocar de modelo, ou de provedor, é
mexer em `app/ia/`, não em quem a usa.

A resposta vem em pedaços (`gerar` é um gerador assíncrono), na ordem em que o
modelo produz. Quem consome decide o que fazer com eles: o chat repassa um a um,
uma extração junta tudo no fim.
"""

from collections.abc import AsyncGenerator, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

Papel = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class MensagemIA:
    papel: Papel
    conteudo: str


class IAIndisponivel(Exception):
    """O provedor não respondeu: fora do ar, lento demais ou sem o modelo.

    A mensagem é para o log, não para o aluno: pode trazer endereço e nome do
    modelo.
    """


class ProvedorIA(Protocol):
    def gerar(self, mensagens: Sequence[MensagemIA], *, max_tokens: int) -> AsyncGenerator[str]:
        """Os pedaços da resposta, na ordem. Levanta `IAIndisponivel` se o provedor falhar."""
        ...
