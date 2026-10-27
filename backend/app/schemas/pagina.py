"""Paginação e ordenação, iguais em toda lista da API.

Uma lista nua na resposta parece mais simples, mas some com a informação de que
o cliente precisa: quantos existem ao todo e se vale pedir mais. Com `Pagina[T]`,
toda lista responde isso da mesma forma, e o frontend escreve o "carregar mais"
uma vez só.
"""

from typing import Annotated

from fastapi import Depends, Query, status
from pydantic import BaseModel, Field

from app.core.erros import ErroDeNegocio

# Teto de itens por página. Existe para uma chamada só não conseguir pedir o
# banco inteiro — inclusive sem querer, num `tamanho_pagina` vindo de bug no
# cliente.
TAMANHO_MAXIMO = 100
TAMANHO_PADRAO = 20


class Pagina[T](BaseModel):
    """Uma fatia de uma lista, com o bastante para montar a navegação."""

    itens: list[T]
    pagina: int = Field(ge=1, description="Página atual, começando em 1")
    tamanho_pagina: int = Field(ge=1, description="Quantos itens cabem na página")
    total: int = Field(ge=0, description="Total de itens em todas as páginas")
    total_paginas: int = Field(ge=0, description="Quantas páginas existem no total")

    @classmethod
    def montar(cls, itens: list[T], *, pagina: int, tamanho_pagina: int, total: int) -> "Pagina[T]":
        # Divisão para cima sem float: `-(-7 // 3) == 3`.
        return cls(
            itens=itens,
            pagina=pagina,
            tamanho_pagina=tamanho_pagina,
            total=total,
            total_paginas=-(-total // tamanho_pagina) if tamanho_pagina else 0,
        )


class Paginacao(BaseModel):
    """Os parâmetros de página, já validados, prontos para virar SQL."""

    pagina: int
    tamanho_pagina: int
    ordenar_por: str | None = None
    decrescente: bool = False

    @property
    def deslocamento(self) -> int:
        return (self.pagina - 1) * self.tamanho_pagina

    def campo_ordenado(self, permitidos: dict[str, object], padrao: str) -> object:
        """Coluna pela qual ordenar, recusando o que não está na lista.

        A lista de permitidos não é preciosismo: `ordenar_por` vem do cliente e
        vira nome de coluna. Sem a lista, ele escolheria por onde o banco
        ordena — e descobriria os nomes das colunas testando.
        """
        nome = self.ordenar_por or padrao
        if nome not in permitidos:
            raise ErroDeNegocio(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                code="ordenacao_invalida",
                message=f"Não dá para ordenar por '{nome}'",
                details={"permitidos": sorted(permitidos)},
            )
        return permitidos[nome]


def paginacao(
    pagina: int = Query(default=1, ge=1, description="Página, começando em 1"),
    tamanho_pagina: int = Query(
        default=TAMANHO_PADRAO,
        ge=1,
        le=TAMANHO_MAXIMO,
        description=f"Itens por página (máximo {TAMANHO_MAXIMO})",
    ),
    ordenar_por: str | None = Query(
        default=None, description="Campo de ordenação; cada rota documenta os seus"
    ),
    decrescente: bool = Query(default=False, description="Inverte a ordem"),
) -> Paginacao:
    """Dependência com os parâmetros de página. Use `PaginacaoAtual` nas rotas."""
    return Paginacao(
        pagina=pagina,
        tamanho_pagina=tamanho_pagina,
        ordenar_por=ordenar_por,
        decrescente=decrescente,
    )


PaginacaoAtual = Annotated[Paginacao, Depends(paginacao)]
