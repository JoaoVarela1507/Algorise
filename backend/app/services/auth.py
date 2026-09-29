"""Registro, login, sessão e recuperação de senha.

As regras ficam aqui e as rotas só traduzem para HTTP, pelo mesmo motivo dos
outros serviços: dá para exercitar tudo isso sem subir a aplicação.

O par de tokens funciona assim: o access é curto e vale por si; o refresh é longo
e só vale enquanto o `jti` dele está registrado no Redis. Renovar troca o par e
revoga o anterior (rotação), então um refresh vazado deixa de servir assim que o
dono usar o dele.
"""

import logging
import secrets
import unicodedata
from hashlib import sha256

from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import chave
from app.core.config import settings
from app.core.redis import executar
from app.core.seguranca import (
    TokenInvalido,
    conferir_senha,
    criar_access_token,
    criar_refresh_token,
    decodificar,
    gerar_hash_senha,
)
from app.models import Usuario
from app.schemas.auth import Sessao, UsuarioAutenticado
from app.services import sessoes

logger = logging.getLogger(__name__)


class EmailEmUso(Exception):
    """Já existe conta com esse e-mail."""


class CredenciaisInvalidas(Exception):
    """E-mail sem conta ou senha errada. A mensagem é a mesma para os dois casos."""


class SessaoExpirada(Exception):
    """Refresh token vencido, revogado, já usado ou impossível de verificar."""


class TokenDeSenhaInvalido(Exception):
    """Link de recuperação vencido, já usado ou inventado."""


def registrar(
    db: Session, *, email: str, senha: str, nome_exibicao: str, username: str | None = None
) -> Usuario:
    email = email.strip().lower()
    if _por_email(db, email) is not None:
        raise EmailEmUso(email)

    usuario = Usuario(
        email=email,
        username=username_livre(db, username or email.split("@")[0]),
        nome_exibicao=nome_exibicao.strip(),
        senha_hash=gerar_hash_senha(senha),
    )
    db.add(usuario)
    db.commit()
    return usuario


def autenticar(db: Session, *, email: str, senha: str) -> Usuario:
    """Confere as credenciais.

    Erro único de propósito: dizer "esse e-mail não existe" entregaria quem tem
    conta para quem está tentando adivinhar. `conferir_senha` também gasta o
    mesmo tempo nos dois casos.
    """
    usuario = _por_email(db, email.strip().lower())
    hash_atual = usuario.senha_hash if usuario is not None else None

    if not conferir_senha(senha, hash_atual) or usuario is None:
        raise CredenciaisInvalidas(email)

    return usuario


def abrir_sessao(usuario: Usuario, *, lembrar: bool = False) -> Sessao:
    """Emite o par de tokens e registra a sessão no Redis."""
    ttl = settings.refresh_token_ttl_lembrar if lembrar else settings.refresh_token_ttl
    refresh, jti = criar_refresh_token(usuario.id, ttl=ttl)

    if not sessoes.registrar_refresh_token(jti, usuario.id, ttl=ttl):
        # Sem o registro, o refresh não funcionaria depois: melhor falhar no
        # login do que entregar um token que já nasce inválido.
        raise SessaoExpirada("Não foi possível registrar a sessão")

    return Sessao(
        access_token=criar_access_token(usuario.id),
        refresh_token=refresh,
        expira_em=settings.access_token_ttl,
        usuario=UsuarioAutenticado.model_validate(usuario),
    )


def renovar_sessao(db: Session, refresh_token: str) -> Sessao:
    """Troca um refresh válido por um par novo, revogando o antigo (rotação)."""
    try:
        conteudo = decodificar(refresh_token, tipo="refresh")
    except TokenInvalido as erro:
        raise SessaoExpirada(str(erro)) from erro

    jti = conteudo.get("jti")
    if not jti:
        raise SessaoExpirada("Refresh token sem jti")

    dono = sessoes.usuario_do_refresh_token(jti)
    if dono is None or dono != int(conteudo["sub"]):
        raise SessaoExpirada("Sessão não registrada")

    usuario = db.get(Usuario, dono)
    if usuario is None:
        raise SessaoExpirada("Conta removida")

    # Revoga antes de emitir: se a emissão falhar, o aluno refaz o login — bem
    # melhor do que ficar com dois refresh válidos ao mesmo tempo.
    sessoes.revogar_refresh_token(jti)
    return abrir_sessao(usuario)


def encerrar_sessao(refresh_token: str) -> None:
    """Logout. Token ilegível não é erro: o objetivo já está cumprido."""
    try:
        conteudo = decodificar(refresh_token, tipo="refresh")
    except TokenInvalido:
        return

    jti = conteudo.get("jti")
    if jti:
        sessoes.revogar_refresh_token(jti)


def criar_token_de_recuperacao(db: Session, email: str) -> str | None:
    """Gera o token do link de "Esqueceu a senha?", ou None se o e-mail não tem conta.

    Quem chama devolve 202 nos dois casos: a resposta não pode revelar quem tem
    conta. No Redis fica o *hash* do token, não ele — assim um dump do Redis não
    vira um passe para trocar senha.
    """
    usuario = _por_email(db, email.strip().lower())
    if usuario is None:
        return None

    token = secrets.token_urlsafe(32)
    gravado = executar(
        lambda r: r.setex(_chave_reset(token), settings.reset_senha_ttl, str(usuario.id)),
        padrao=False,
    )
    if not gravado:
        logger.warning("Redis fora: recuperação de senha indisponível para %s", usuario.id)
        return None

    return token


def redefinir_senha(db: Session, *, token: str, senha: str) -> Usuario:
    """Troca a senha e derruba as sessões abertas.

    O token é de uso único: some do Redis antes da troca, para dois cliques no
    mesmo link não valerem duas vezes.
    """

    def consumir(r: Redis) -> str | None:
        return r.getdel(_chave_reset(token))

    dono = executar(consumir, padrao=None)
    if dono is None:
        raise TokenDeSenhaInvalido(token[:8])

    usuario = db.get(Usuario, int(dono))
    if usuario is None:
        raise TokenDeSenhaInvalido(token[:8])

    usuario.senha_hash = gerar_hash_senha(senha)
    db.commit()

    # Quem trocou a senha provavelmente trocou por suspeitar de invasão; as
    # sessões que já estavam abertas não podem sobreviver a isso.
    sessoes.revogar_sessoes_do_usuario(usuario.id)
    return usuario


def _chave_reset(token: str) -> str:
    return chave("senha", "reset", sha256(token.encode("utf-8")).hexdigest())


def _por_email(db: Session, email: str) -> Usuario | None:
    return db.execute(select(Usuario).where(Usuario.email == email)).scalar_one_or_none()


def username_livre(db: Session, sugestao: str) -> str:
    """Username a partir da sugestão, com sufixo numérico se já existir."""
    base = _normalizar_username(sugestao)
    candidato = base
    sufixo = 1

    while db.execute(select(Usuario.id).where(Usuario.username == candidato)).scalar() is not None:
        sufixo += 1
        # O corte mantém espaço para o sufixo dentro dos 50 caracteres da coluna.
        candidato = f"{base[: 50 - len(str(sufixo))]}{sufixo}"

    return candidato


def _normalizar_username(bruto: str) -> str:
    """Tira acento e o que não for letra, número, ponto, hífen ou sublinhado."""
    sem_acento = unicodedata.normalize("NFKD", bruto).encode("ascii", "ignore").decode("ascii")
    limpo = "".join(c for c in sem_acento.lower() if c.isalnum() or c in "._-")
    return (limpo or f"aluno{secrets.randbelow(100_000)}")[:50]
