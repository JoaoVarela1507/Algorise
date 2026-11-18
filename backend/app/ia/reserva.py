"""Provedor principal com reserva, e um modelo por uso da IA.

O Gemini gratuito tem cota por modelo e, às vezes, fila cheia ("high demand").
Para uma apresentação não parar por isso:

- **`ComReserva`**: o pedido vai ao principal (o Gemini); se ele falhar antes de
  mandar o primeiro pedaço, vai à reserva (o Ollama da máquina). Depois de mandar
  algo, não troca: emendar a resposta de outro modelo no meio daria um texto sem
  pé nem cabeça, e o erro sobe como antes. Depois de uma falha, o modelo fica
  pausado por `IA_PAUSA_APOS_FALHA` segundos, e os pedidos vão direto à reserva
  em vez de esperar o mesmo erro de novo.
- **`PorUso`**: um provedor por uso da IA (chat, correção, exercícios...), cada
  um com o seu modelo do Gemini, para um uso não gastar a cota do outro. Os
  embeddings vêm sempre do provedor de embeddings (o Ollama), que não tem cota.

Quem usa a IA pede o do seu uso com `para(provedor, "correcao")`. Um provedor
sem usos (o Ollama sozinho, o eco, os falsos dos testes) é devolvido como está.
"""

import logging
import time
from collections.abc import AsyncGenerator, Callable, Sequence
from typing import Any

from app.ia.base import IAIndisponivel, MensagemIA, ProvedorIA

logger = logging.getLogger(__name__)

# Até quando cada modelo principal está pausado (relógio monotônico). Fica no
# módulo, e não na instância, porque a API monta um provedor novo por pedido.
_PAUSAS: dict[str, float] = {}


class ComReserva:
    def __init__(
        self,
        principal: ProvedorIA,
        reserva: ProvedorIA,
        *,
        nome: str,
        pausa_segundos: float,
        relogio: Callable[[], float] = time.monotonic,
    ) -> None:
        self.principal = principal
        self.reserva = reserva
        self.nome = nome
        self.pausa_segundos = pausa_segundos
        self.relogio = relogio

    async def gerar(
        self,
        mensagens: Sequence[MensagemIA],
        *,
        max_tokens: int,
        formato: dict[str, Any] | None = None,
    ) -> AsyncGenerator[str]:
        # Pausado, a reserva vem primeiro; mas se ela também falhar, o principal
        # ainda é tentado: com o Ollama desligado, uma falha passageira do Gemini
        # não pode derrubar todos os pedidos do minuto seguinte.
        ordem = [self.reserva, self.principal] if self.pausado else [self.principal, self.reserva]
        ultimo_erro: IAIndisponivel | None = None
        for provedor in ordem:
            enviou = False
            try:
                async for pedaco in provedor.gerar(
                    mensagens, max_tokens=max_tokens, formato=formato
                ):
                    enviou = True
                    yield pedaco
            except IAIndisponivel as erro:
                if enviou:
                    raise
                ultimo_erro = erro
                if provedor is self.principal:
                    _PAUSAS[self.nome] = self.relogio() + self.pausa_segundos
                    logger.warning("IA principal (%s) falhou: %s", self.nome, erro)
                else:
                    logger.warning("IA de reserva falhou (%s): %s", self.nome, erro)
                continue
            if provedor is self.principal:
                _PAUSAS.pop(self.nome, None)
            return
        assert ultimo_erro is not None
        raise ultimo_erro

    async def embeddings(self, textos: Sequence[str]) -> list[list[float]]:
        return await self.principal.embeddings(textos)

    @property
    def pausado(self) -> bool:
        return _PAUSAS.get(self.nome, 0) > self.relogio()


class PorUso:
    """Um provedor por uso da IA, e os embeddings de um provedor só."""

    def __init__(
        self,
        fabrica: Callable[[str], ProvedorIA],
        embeddings: ProvedorIA,
        *,
        uso_padrao: str,
    ) -> None:
        self.fabrica = fabrica
        self.provedor_de_embeddings = embeddings
        self.uso_padrao = uso_padrao
        self._por_uso: dict[str, ProvedorIA] = {}

    def para(self, uso: str) -> ProvedorIA:
        if uso not in self._por_uso:
            self._por_uso[uso] = self.fabrica(uso)
        return self._por_uso[uso]

    def gerar(
        self,
        mensagens: Sequence[MensagemIA],
        *,
        max_tokens: int,
        formato: dict[str, Any] | None = None,
    ) -> AsyncGenerator[str]:
        return self.para(self.uso_padrao).gerar(mensagens, max_tokens=max_tokens, formato=formato)

    async def embeddings(self, textos: Sequence[str]) -> list[list[float]]:
        return await self.provedor_de_embeddings.embeddings(textos)

    @property
    def marca_embedding(self) -> str | None:
        """A marca de quem gera os vetores: entra no hash do vault (ver `ingestao`)."""
        return getattr(self.provedor_de_embeddings, "marca_embedding", None)


def para(provedor: ProvedorIA, uso: str) -> ProvedorIA:
    """O provedor deste uso, quando há um por uso; senão, o próprio."""
    escolher = getattr(provedor, "para", None)
    return escolher(uso) if callable(escolher) else provedor


def limpar_pausas() -> None:
    """Para os testes: nenhum modelo pausado."""
    _PAUSAS.clear()
