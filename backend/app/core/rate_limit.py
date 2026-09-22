"""Rate limit por janela fixa, para endpoints que custam dinheiro por request.

O chat chama IA a cada mensagem, então o limite é por aluno e por janela. A
contagem é um `INCR` com `EXPIRE` na primeira ocorrência, os dois no mesmo
pipeline: uma ida ao Redis por request.

Janela fixa, não deslizante: no pior caso o aluno emenda o fim de uma janela com
o começo da outra e manda o dobro do limite num intervalo curto. Para proteger
custo de IA isso basta, e o custo é uma chave por janela em vez de um sorted set
com um item por request.

Aqui o Redis fora falha **aberto**: derrubar o chat por causa do cache seria
trocar um problema de custo por um de indisponibilidade.
"""

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from redis import Redis

from app.core.cache import chave
from app.core.config import settings
from app.core.redis import executar


@dataclass(frozen=True)
class Resultado:
    permitido: bool
    restantes: int
    # Segundos até a janela virar. Vai no `Retry-After` da resposta 429.
    reiniciar_em: int


def verificar(identificador: str, *, limite: int, janela: int) -> Resultado:
    """Conta mais um acesso de `identificador` e diz se ele passa."""
    nome = chave("ratelimit", identificador)

    def contar(r: Redis) -> tuple[int, int]:
        with r.pipeline() as pipe:
            pipe.incr(nome)
            # `nx=True` só define o TTL na primeira requisição da janela; sem
            # isso cada acesso empurraria o vencimento e a janela nunca viraria.
            pipe.expire(nome, janela, nx=True)
            pipe.ttl(nome)
            usados, _, restante = pipe.execute()
        return int(usados), int(restante)

    contagem = executar(contar, padrao=None)
    if contagem is None:
        # Redis fora: libera e informa o limite cheio.
        return Resultado(permitido=True, restantes=limite, reiniciar_em=janela)

    usados, restante = contagem
    return Resultado(
        permitido=usados <= limite,
        restantes=max(limite - usados, 0),
        # TTL negativo significa chave sem expiração, que não deveria acontecer;
        # tratar como janela cheia evita um `Retry-After` inválido.
        reiniciar_em=restante if restante > 0 else janela,
    )


def limitar_chat(request: Request) -> None:
    """Dependência do FastAPI para as rotas de chat: 429 quando passa do limite.

    A chave é o IP enquanto a autenticação (#10) não existe; com ela, passa a ser
    o id do aluno, que é o que a issue pede.
    """
    identificador = f"chat:{request.client.host if request.client else 'desconhecido'}"
    resultado = verificar(
        identificador,
        limite=settings.rate_limit_chat_requisicoes,
        janela=settings.rate_limit_chat_janela,
    )

    if not resultado.permitido:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas mensagens em pouco tempo. Tente de novo em instantes.",
            headers={"Retry-After": str(resultado.reiniciar_em)},
        )


# Açúcar para a rota: `dependencies=[LimiteDoChat]`.
LimiteDoChat = Depends(limitar_chat)
