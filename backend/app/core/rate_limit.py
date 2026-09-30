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
from app.core.seguranca import TokenInvalido, decodificar


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


def limite_por_ip(nome: str, *, limite: int, janela: int, mensagem: str | None = None):
    """Dependência que limita a rota por IP: `dependencies=[limite_por_ip("login", ...)]`.

    Usada nas rotas de autenticação, que não têm aluno para servir de chave.
    Atrás de proxy, o uvicorn precisa de `--proxy-headers` (e o IP do proxy em
    `--forwarded-allow-ips`) para `request.client` ser o IP de quem chamou, e não
    o do proxy — senão todo mundo divide o mesmo limite.
    """

    def limitar(request: Request) -> None:
        _barrar_se_passou(f"{nome}:ip:{_ip(request)}", limite, janela, mensagem)

    return Depends(limitar)


def limitar_chat(request: Request) -> None:
    """Dependência do FastAPI para as rotas de chat: 429 quando passa do limite.

    A chave é o aluno quando o request traz um access token válido, e o IP
    quando não: o chat custa IA por mensagem, e o limite por aluno é o que
    impede uma conta de gastar pelo IP de uma sala inteira.
    """
    usuario = _usuario_do_token(request)
    identificador = f"chat:usuario:{usuario}" if usuario else f"chat:ip:{_ip(request)}"
    _barrar_se_passou(
        identificador,
        settings.rate_limit_chat_requisicoes,
        settings.rate_limit_chat_janela,
        "Muitas mensagens em pouco tempo. Tente de novo em instantes.",
    )


# Açúcar para a rota: `dependencies=[LimiteDoChat]`.
LimiteDoChat = Depends(limitar_chat)


def _barrar_se_passou(identificador: str, limite: int, janela: int, mensagem: str | None) -> None:
    resultado = verificar(identificador, limite=limite, janela=janela)
    if not resultado.permitido:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=mensagem or "Muitas tentativas em pouco tempo. Tente de novo em instantes.",
            headers={"Retry-After": str(resultado.reiniciar_em)},
        )


def _ip(request: Request) -> str:
    return request.client.host if request.client else "desconhecido"


def _usuario_do_token(request: Request) -> str | None:
    """Dono do access token do header, sem ir ao banco. None se não houver um válido."""
    cabecalho = request.headers.get("authorization", "")
    esquema, _, token = cabecalho.partition(" ")
    if esquema.lower() != "bearer" or not token:
        return None
    try:
        return str(decodificar(token, tipo="access")["sub"])
    except TokenInvalido:
        return None
