"""Refresh tokens e sessões revogadas.

Este é o único lugar do backend em que o Redis é a fonte da verdade, e não cache:
o refresh token vale porque está registrado aqui, e a revogação vale porque está
marcada aqui. O TTL faz o trabalho que uma tabela pediria — uma varredura para
apagar token vencido.

A consequência é que aqui não existe degradação graciosa: com o Redis fora, a
validação falha fechado e o aluno refaz o login. O contrário — aceitar um token
que não podemos verificar — transformaria uma queda de cache em brecha de
autenticação. O resto da API continua servindo normalmente.

Além do registro por token, cada aluno tem um conjunto com os `jti` dos refresh
tokens que emitiu. É ele que permite derrubar todas as sessões de uma vez — na
redefinição de senha e quando um refresh já usado reaparece.

As rotas que usam isso estão em `app/api/routes/auth.py`.
"""

from redis import Redis

from app.core.cache import chave
from app.core.config import settings
from app.core.redis import executar


def _chave_token(jti: str) -> str:
    return chave("sessao", "refresh", jti)


def _chave_revogada(jti: str) -> str:
    return chave("sessao", "revogada", jti)


def _chave_usuario(usuario_id: int) -> str:
    return chave("sessao", "usuario", usuario_id)


def registrar_refresh_token(jti: str, usuario_id: int, *, ttl: int | None = None) -> bool:
    """Registra o token e devolve se deu certo.

    `False` quer dizer que o Redis não aceitou a gravação; quem chamou não deve
    entregar o token ao cliente, porque ele não vai funcionar no refresh.
    """
    ttl = ttl or settings.refresh_token_ttl

    def registrar(r: Redis) -> bool:
        with r.pipeline() as pipe:
            pipe.setex(_chave_token(jti), ttl, str(usuario_id))
            pipe.sadd(_chave_usuario(usuario_id), jti)
            # O conjunto vive o prazo do token mais longo possível, renovado a
            # cada emissão. Um `jti` já vencido que sobre ali não faz mal: apagar
            # chave inexistente é no-op.
            pipe.expire(_chave_usuario(usuario_id), settings.refresh_token_ttl_estendido)
            gravado, *_ = pipe.execute()
        return bool(gravado)

    return bool(executar(registrar, padrao=False))


def consumir_refresh_token(jti: str, *, ttl: int | None = None) -> int | None:
    """Gasta o token na rotação: devolve o dono e o invalida na mesma operação.

    O `GETDEL` é o que torna a rotação segura. Com um `GET` seguido de `DELETE`,
    dois refresh simultâneos com o mesmo token passariam os dois pela leitura e
    sairiam cada um com um par novo.
    """
    ttl = ttl or settings.refresh_token_ttl

    def consumir(r: Redis) -> int | None:
        with r.pipeline() as pipe:
            pipe.getdel(_chave_token(jti))
            pipe.exists(_chave_revogada(jti))
            pipe.setex(_chave_revogada(jti), ttl, "1")
            dono, revogada, _ = pipe.execute()

        if dono is None or revogada:
            return None
        r.srem(_chave_usuario(int(dono)), jti)
        return int(dono)

    return executar(consumir, padrao=None)


def usuario_do_refresh_token(jti: str) -> int | None:
    """Dono do token, ou None se ele expirou, foi revogado ou nunca existiu.

    Também devolve None quando o Redis está fora: falhar fechado é o
    comportamento desejado aqui.
    """

    def ler(r: Redis) -> int | None:
        with r.pipeline() as pipe:
            pipe.get(_chave_token(jti))
            pipe.exists(_chave_revogada(jti))
            dono, revogada = pipe.execute()

        if dono is None or revogada:
            return None
        return int(dono)

    return executar(ler, padrao=None)


def revogar_refresh_token(jti: str, *, ttl: int | None = None) -> None:
    """Invalida o token na hora (logout) e guarda a revogação.

    O marcador de revogação existe para o caso de o access token emitido junto
    ainda estar no prazo: ele vive o mesmo tempo que o refresh viveria, e depois
    disso o token já teria expirado sozinho.
    """
    ttl = ttl or settings.refresh_token_ttl

    def revogar(r: Redis) -> None:
        with r.pipeline() as pipe:
            pipe.delete(_chave_token(jti))
            pipe.setex(_chave_revogada(jti), ttl, "1")
            pipe.execute()

    executar(revogar)


def esta_revogado(jti: str) -> bool:
    """Se a sessão foi revogada. Com o Redis fora devolve True, pelo mesmo motivo."""
    revogada = executar(lambda r: r.exists(_chave_revogada(jti)), padrao=1)
    return bool(revogada)


def revogar_todas(usuario_id: int) -> None:
    """Derruba todas as sessões do aluno: cada refresh emitido deixa de valer."""

    def revogar(r: Redis) -> None:
        jtis = r.smembers(_chave_usuario(usuario_id))
        with r.pipeline() as pipe:
            for jti in jtis:
                pipe.delete(_chave_token(jti))
                pipe.setex(_chave_revogada(jti), settings.refresh_token_ttl_estendido, "1")
            pipe.delete(_chave_usuario(usuario_id))
            pipe.execute()

    executar(revogar)
