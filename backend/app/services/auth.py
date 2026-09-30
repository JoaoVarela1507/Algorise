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
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.cache import chave
from app.core.config import settings
from app.core.politica_senha import problema_da_senha
from app.core.redis import executar
from app.core.seguranca import (
    TokenInvalido,
    conferir_senha,
    criar_access_token,
    criar_refresh_token,
    decodificar,
    gerar_hash_senha,
)
from app.models import Consentimento, Usuario
from app.schemas.auth import Sessao, UsuarioAutenticado
from app.services import sessoes

logger = logging.getLogger(__name__)


class EmailEmUso(Exception):
    """Já existe conta com esse e-mail."""


class UsernameEmUso(Exception):
    """O aluno escolheu um username que já é de outra conta."""


class CredenciaisInvalidas(Exception):
    """E-mail sem conta ou senha errada. A mensagem é a mesma para os dois casos."""


class SessaoExpirada(Exception):
    """Refresh token vencido, revogado, já usado ou impossível de verificar."""


class SessaoIndisponivel(Exception):
    """O Redis não gravou a sessão. Não é culpa do aluno: vira 503, não 401."""


class TokenDeSenhaInvalido(Exception):
    """Link de recuperação vencido, já usado ou inventado."""


class SenhaFraca(Exception):
    """Senha nova fora da política (ver `app/core/politica_senha.py`)."""


class LoginBloqueado(Exception):
    """Tentativas erradas demais no mesmo e-mail. `segundos` até liberar."""

    def __init__(self, segundos: int) -> None:
        super().__init__(segundos)
        self.segundos = segundos


def registrar(
    db: Session,
    *,
    email: str,
    senha: str,
    nome_exibicao: str | None = None,
    username: str | None = None,
    ip: str | None = None,
) -> Usuario:
    """Cria a conta.

    Username escolhido pelo aluno (tela 6) que já exista é recusado: trocar por
    `ana2` em silêncio deixaria o aluno sem saber com que nome entrou. Só quando
    ele não escolhe nenhum é que o username sai do e-mail, com sufixo se preciso.
    """
    email = email.strip().lower()
    if _por_email(db, email) is not None:
        raise EmailEmUso(email)

    if username is not None:
        if _username_em_uso(db, username):
            raise UsernameEmUso(username)
    else:
        username = username_livre(db, email.split("@")[0])

    if motivo := problema_da_senha(senha, email=email, username=username):
        raise SenhaFraca(motivo)

    usuario = Usuario(
        email=email,
        username=username,
        nome_exibicao=(nome_exibicao or username).strip(),
        senha_hash=gerar_hash_senha(senha),
    )
    # O schema só deixa chegar aqui com o checkbox dos termos marcado; o
    # registro guarda a prova (versão, data e IP) que a LGPD pede.
    usuario.consentimentos.append(
        Consentimento(versao_termos=settings.versao_termos, origem="cadastro", ip=ip)
    )
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError as erro:
        # Dois cadastros simultâneos passam juntos pelas checagens acima; o
        # segundo esbarra na constraint do banco e vira 409 em vez de 500.
        db.rollback()
        if "username" in str(erro.orig):
            raise UsernameEmUso(username) from erro
        raise EmailEmUso(email) from erro
    return usuario


def autenticar(db: Session, *, email: str, senha: str) -> Usuario:
    """Confere as credenciais.

    Erro único de propósito: dizer "esse e-mail não existe" entregaria quem tem
    conta para quem está tentando adivinhar. `conferir_senha` também gasta o
    mesmo tempo nos dois casos.

    Tentativas erradas seguidas no mesmo e-mail bloqueiam o login por um tempo,
    com ou sem conta por trás — bloquear só quem tem conta também entregaria
    quem tem conta. Com o bloqueio ativo, nem a senha certa passa.
    """
    email = email.strip().lower()
    if restante := _bloqueio_restante(email):
        raise LoginBloqueado(restante)

    usuario = _por_email(db, email)
    hash_atual = usuario.senha_hash if usuario is not None else None

    if not conferir_senha(senha, hash_atual) or usuario is None:
        _registrar_falha(email)
        raise CredenciaisInvalidas(email)

    _limpar_falhas(email)
    return usuario


def abrir_sessao(usuario: Usuario, *, lembrar: bool = False) -> Sessao:
    """Emite o par de tokens e registra a sessão no Redis."""
    ttl = settings.refresh_token_ttl_lembrar if lembrar else settings.refresh_token_ttl
    refresh, jti = criar_refresh_token(usuario.id, ttl=ttl)

    if not sessoes.registrar_refresh_token(jti, usuario.id, ttl=ttl):
        # Sem o registro, o refresh não funcionaria depois: melhor falhar no
        # login do que entregar um token que já nasce inválido.
        raise SessaoIndisponivel("Não foi possível registrar a sessão")

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

    # Consome antes de emitir, na mesma operação que confere: se a emissão
    # falhar, o aluno refaz o login — bem melhor do que dois refresh válidos.
    dono = sessoes.consumir_refresh_token(jti)
    if dono is None or dono != int(conteudo["sub"]):
        raise SessaoExpirada("Sessão não registrada")

    usuario = db.get(Usuario, dono)
    if usuario is None or usuario.exclusao_agendada_para is not None:
        # Conta apagada, ou com exclusão pedida: só um login novo reativa.
        raise SessaoExpirada("Conta removida ou desativada")

    # A sessão renovada mantém o "manter-se conectado" do login. O prazo do
    # token usado diz qual foi a escolha, sem precisar de claim nova.
    lembrar = conteudo["exp"] - conteudo["iat"] > settings.refresh_token_ttl
    return abrir_sessao(usuario, lembrar=lembrar)


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
        lambda r: r.set(_chave_reset(token), str(usuario.id), ex=settings.reset_senha_ttl),
        padrao=False,
    )
    if not gravado:
        logger.warning("Redis fora: recuperação de senha indisponível para %s", usuario.id)
        return None

    return token


def redefinir_senha(db: Session, *, token: str, senha: str) -> Usuario:
    """Troca a senha e derruba as sessões abertas.

    O token é de uso único: some do Redis antes da troca, para dois cliques no
    mesmo link não valerem duas vezes. Mas só depois de a senha nova passar na
    política — senão uma senha recusada queimaria o link.
    """
    dono = executar(lambda r: r.get(_chave_reset(token)), padrao=None)
    usuario = db.get(Usuario, int(dono)) if dono is not None else None
    if usuario is None:
        raise TokenDeSenhaInvalido(token[:8])

    if motivo := problema_da_senha(senha, email=usuario.email, username=usuario.username):
        raise SenhaFraca(motivo)

    def consumir(r: Redis) -> str | None:
        return r.getdel(_chave_reset(token))

    # O `GETDEL` é quem decide: entre a leitura acima e aqui, outro clique no
    # mesmo link pode ter chegado antes.
    if executar(consumir, padrao=None) != dono:
        raise TokenDeSenhaInvalido(token[:8])

    usuario.senha_hash = gerar_hash_senha(senha)
    db.commit()
    # Provou ser dono do e-mail: o bloqueio por tentativas não vale mais.
    _limpar_falhas(usuario.email)

    # Quem trocou a senha provavelmente trocou por suspeitar de invasão; as
    # sessões que já estavam abertas não podem sobreviver a isso.
    sessoes.revogar_sessoes_do_usuario(usuario.id)
    return usuario


def _chave_falhas(email: str) -> str:
    # Hash, não o e-mail: a chave aparece em `SCAN` e em dump do Redis.
    return chave("login", "falhas", sha256(email.encode("utf-8")).hexdigest())


def _bloqueio_restante(email: str) -> int:
    """Segundos até liberar o login desse e-mail, ou 0 se não está bloqueado.

    Com o Redis fora não há como contar, e o login segue: o limite por IP das
    rotas continua valendo, e travar o login de todo mundo seria pior.
    """

    def ler(r: Redis) -> int:
        with r.pipeline() as pipe:
            pipe.get(_chave_falhas(email))
            pipe.ttl(_chave_falhas(email))
            falhas, ttl = pipe.execute()
        if falhas is None or int(falhas) < settings.bloqueio_login_tentativas:
            return 0
        return max(int(ttl), 1)

    return executar(ler, padrao=0) or 0


def _registrar_falha(email: str) -> None:
    def contar(r: Redis) -> None:
        with r.pipeline() as pipe:
            pipe.incr(_chave_falhas(email))
            # A contagem zera sozinha depois do prazo; e a falha que completa o
            # limite reinicia o relógio, para o bloqueio durar o prazo inteiro.
            pipe.expire(_chave_falhas(email), settings.bloqueio_login_duracao, nx=True)
            falhas, _ = pipe.execute()
        if int(falhas) == settings.bloqueio_login_tentativas:
            r.expire(_chave_falhas(email), settings.bloqueio_login_duracao)

    executar(contar)


def _limpar_falhas(email: str) -> None:
    executar(lambda r: r.delete(_chave_falhas(email)))


def _chave_reset(token: str) -> str:
    return chave("senha", "reset", sha256(token.encode("utf-8")).hexdigest())


def _username_em_uso(db: Session, username: str) -> bool:
    encontrado = db.execute(
        select(Usuario.id).where(func.lower(Usuario.username) == username.lower())
    ).first()
    return encontrado is not None


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
