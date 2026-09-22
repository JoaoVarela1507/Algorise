"""Cache JSON com TTL sobre o Redis.

Duas regras valem para tudo que passa por aqui:

- guardar só o que o banco sabe reconstruir. Um miss e um Redis fora do ar
  precisam ser indistinguíveis para quem chama;
- toda chave começa com `PREFIXO`, para o `algorise:` separar nosso espaço do de
  qualquer outra coisa que use a mesma instância.
"""

import json
from collections.abc import Iterable, Iterator
from typing import Any

from redis import Redis

from app.core.redis import executar

PREFIXO = "algorise"


def chave(*partes: object) -> str:
    """Monta a chave a partir das partes: `chave("trilhas", 3)` -> `algorise:trilhas:3`."""
    return ":".join([PREFIXO, *(str(parte) for parte in partes)])


def obter_json(nome: str) -> Any | None:
    """Valor do cache já desserializado, ou None em miss (e com o Redis fora)."""
    bruto = executar(lambda r: r.get(nome))
    if bruto is None:
        return None

    try:
        return json.loads(bruto)
    except json.JSONDecodeError:
        # Formato antigo de um deploy anterior. Descarta e trata como miss, em
        # vez de propagar o erro para a rota.
        executar(lambda r: r.delete(nome))
        return None


def definir_json(nome: str, valor: Any, ttl: int) -> None:
    """Grava o valor serializado com TTL. `ensure_ascii=False` por causa dos acentos."""
    conteudo = json.dumps(valor, ensure_ascii=False, default=str)
    executar(lambda r: r.setex(nome, ttl, conteudo))


def invalidar(*nomes: str) -> None:
    if nomes:
        executar(lambda r: r.delete(*nomes))


def invalidar_prefixo(prefixo: str) -> int:
    """Apaga todas as chaves sob um prefixo.

    Usa `SCAN` em lotes, não `KEYS`: o `KEYS` percorre o keyspace inteiro
    travando o Redis, e uma invalidação de cache não justifica isso.
    """
    padrao = f"{prefixo}*"

    def varrer(r: Redis) -> int:
        apagadas = 0
        for lote in _lotes(r.scan_iter(match=padrao, count=500), 500):
            apagadas += r.delete(*lote)
        return apagadas

    return executar(varrer, padrao=0) or 0


def _lotes(itens: Iterable[str], tamanho: int) -> Iterator[list[str]]:
    lote: list[str] = []
    for item in itens:
        lote.append(item)
        if len(lote) >= tamanho:
            yield lote
            lote = []
    if lote:
        yield lote
