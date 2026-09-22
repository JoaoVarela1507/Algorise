"""Refresh tokens e sessões revogadas.

Este é o único lugar do backend em que o Redis é a fonte da verdade, e não cache:
o refresh token vale porque está registrado aqui, e a revogação vale porque está
marcada aqui. O TTL faz o trabalho que uma tabela pediria — uma varredura para
apagar token vencido.

A consequência é que aqui não existe degradação graciosa: com o Redis fora, a
validação falha fechado e o aluno refaz o login. O contrário — aceitar um token
que não podemos verificar — transformaria uma queda de cache em brecha de
autenticação. O resto da API continua servindo normalmente.

As rotas de autenticação que usam isso vêm em #10.
"""

from redis import Redis

from app.core.cache import chave
from app.core.config import settings
from app.core.redis import executar


def _chave_token(jti: str) -> str:
    return chave("sessao", "refresh", jti)


def _chave_revogada(jti: str) -> str:
    return chave("sessao", "revogada", jti)


def _chave_do_usuario(usuario_id: int) -> str:
    """Set com os `jti` abertos do aluno, para conseguir derrubar todos de uma vez."""
    return chave("sessao", "usuario", usuario_id)


def registrar_refresh_token(jti: str, usuario_id: int, *, ttl: int | None = None) -> bool:
    """Registra o token e devolve se deu certo.

    `False` quer dizer que o Redis não aceitou a gravação; quem chamou não deve
    entregar o token ao cliente, porque ele não vai funcionar no refresh.
    """
    ttl = ttl or settings.refresh_token_ttl

    def gravar(r: Redis) -> bool:
        with r.pipeline() as pipe:
            pipe.setex(_chave_token(jti), ttl, str(usuario_id))
            # O set acompanha o token mais longo do aluno; sem o `expire` ele
            # sobreviveria a todas as sessões e ficaria crescendo para sempre.
            pipe.sadd(_chave_do_usuario(usuario_id), jti)
            pipe.expire(_chave_do_usuario(usuario_id), ttl, gt=True)
            gravou, *_ = pipe.execute()
        return bool(gravou)

    return bool(executar(gravar, padrao=False))


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
        dono = r.get(_chave_token(jti))
        with r.pipeline() as pipe:
            pipe.delete(_chave_token(jti))
            pipe.setex(_chave_revogada(jti), ttl, "1")
            if dono is not None:
                pipe.srem(_chave_do_usuario(int(dono)), jti)
            pipe.execute()

    executar(revogar)


def revogar_sessoes_do_usuario(usuario_id: int, *, ttl: int | None = None) -> int:
    """Derruba todas as sessões do aluno e devolve quantas eram.

    Usado na troca de senha: quem troca a senha espera que quem estava dentro
    caia fora.
    """
    ttl = ttl or settings.refresh_token_ttl

    def revogar_todas(r: Redis) -> int:
        jtis = r.smembers(_chave_do_usuario(usuario_id))
        if not jtis:
            return 0

        with r.pipeline() as pipe:
            for jti in jtis:
                pipe.delete(_chave_token(jti))
                pipe.setex(_chave_revogada(jti), ttl, "1")
            pipe.delete(_chave_do_usuario(usuario_id))
            pipe.execute()
        return len(jtis)

    return executar(revogar_todas, padrao=0) or 0


def esta_revogado(jti: str) -> bool:
    """Se a sessão foi revogada. Com o Redis fora devolve True, pelo mesmo motivo."""
    revogada = executar(lambda r: r.exists(_chave_revogada(jti)), padrao=1)
    return bool(revogada)
