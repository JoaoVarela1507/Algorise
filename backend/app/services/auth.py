"""Regras de autenticação: conta, sessão, login social e redefinição de senha.

As rotas em `app/api/routes/auth.py` só traduzem as exceções daqui para HTTP.
"""

import hashlib
import logging
import re
import secrets

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import seguranca
from app.core.cache import chave
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.redis import executar
from app.models import IdentidadeOAuth, ProvedorOAuth, Usuario
from app.schemas.auth import RegistroEntrada
from app.schemas.auth import Sessao as SessaoSchema
from app.schemas.usuario import Usuario as UsuarioSchema
from app.services import sessoes

logger = logging.getLogger(__name__)


class ContaJaExiste(Exception):
    def __init__(self, campo: str) -> None:
        super().__init__(campo)
        self.campo = campo


class CredenciaisInvalidas(Exception):
    """E-mail sem conta, senha errada ou conta só de OAuth — de propósito, tudo igual."""


class SessaoInvalida(Exception):
    """Refresh token vencido, adulterado, revogado ou já usado."""


class SessaoIndisponivel(Exception):
    """O Redis não gravou o refresh token; entregar o token seria entregar um token morto."""


class LinkInvalido(Exception):
    """Token de redefinição de senha vencido, já usado ou inexistente."""


class EmailNaoVerificado(Exception):
    """O provedor não garante que o e-mail é do aluno; vincular por ele seria brecha."""


class ProvedorJaVinculado(Exception):
    """A conta com esse e-mail já está ligada a outra conta do mesmo provedor."""


# --- conta e sessão -----------------------------------------------------------


def registrar(db: Session, dados: RegistroEntrada) -> Usuario:
    if _por_email(db, dados.email) is not None:
        raise ContaJaExiste("email")
    if _username_em_uso(db, dados.username):
        raise ContaJaExiste("username")

    usuario = Usuario(
        email=dados.email,
        username=dados.username,
        nome_exibicao=dados.username,
        senha_hash=seguranca.gerar_hash(dados.senha),
    )
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError as erro:
        # Dois cadastros simultâneos com o mesmo e-mail passam pela checagem
        # acima; quem chega por último cai aqui, na constraint do banco.
        db.rollback()
        campo = "username" if "username" in str(erro.orig) else "email"
        raise ContaJaExiste(campo) from erro
    return usuario


def autenticar(db: Session, email: str, senha: str) -> Usuario:
    usuario = _por_email(db, email)
    # `verificar_senha` roda o bcrypt mesmo sem usuário: o tempo de resposta
    # não pode denunciar se o e-mail tem conta.
    senha_hash = usuario.senha_hash if usuario else None
    if not seguranca.verificar_senha(senha, senha_hash) or usuario is None:
        raise CredenciaisInvalidas
    return usuario


def abrir_sessao(usuario: Usuario, *, estendido: bool = False) -> SessaoSchema:
    """Emite o par de tokens e registra o refresh no Redis."""
    ttl_refresh = settings.refresh_token_ttl_estendido if estendido else settings.refresh_token_ttl
    access = seguranca.emitir(usuario.id, "access", ttl=settings.access_token_ttl)
    refresh = seguranca.emitir(usuario.id, "refresh", ttl=ttl_refresh, estendido=estendido)

    if not sessoes.registrar_refresh_token(refresh.jti, usuario.id, ttl=ttl_refresh):
        raise SessaoIndisponivel

    return SessaoSchema(
        access_token=access.valor,
        refresh_token=refresh.valor,
        expira_em=settings.access_token_ttl,
        usuario=UsuarioSchema.do_modelo(usuario),
    )


def renovar(db: Session, refresh_token: str) -> SessaoSchema:
    """Rotação: o refresh usado morre aqui e um par novo nasce no lugar."""
    try:
        claims = seguranca.decodificar(refresh_token, "refresh")
    except seguranca.TokenInvalido as erro:
        raise SessaoInvalida from erro

    dono = sessoes.consumir_refresh_token(claims.jti, ttl=seguranca.segundos_ate(claims.expira_em))
    if dono is None or dono != claims.usuario_id:
        raise SessaoInvalida

    usuario = db.get(Usuario, dono)
    if usuario is None:
        raise SessaoInvalida

    # A sessão renovada mantém a escolha de "manter-se conectado" do login.
    return abrir_sessao(usuario, estendido=claims.estendido)


def encerrar(refresh_token: str) -> None:
    """Logout. Token inválido não é erro: o objetivo (sessão morta) já está cumprido."""
    try:
        claims = seguranca.decodificar(refresh_token, "refresh")
    except seguranca.TokenInvalido:
        return
    sessoes.revogar_refresh_token(claims.jti, ttl=seguranca.segundos_ate(claims.expira_em))


# --- login social -------------------------------------------------------------


def entrar_com_provedor(
    db: Session,
    *,
    provedor: ProvedorOAuth,
    id_externo: str,
    email: str,
    email_verificado: bool,
    nome: str | None,
    avatar_url: str | None,
    username_sugerido: str | None,
) -> Usuario:
    """Acha o aluno da conta do provedor, vincula a uma conta existente ou cria uma.

    A ordem importa: primeiro o vínculo pelo id do provedor (que não muda), só
    depois o e-mail. E o e-mail só vale se o provedor diz que é verificado — do
    contrário qualquer um criaria uma conta no provedor com o e-mail de outra
    pessoa e entraria na conta dela aqui.
    """
    identidade = db.execute(
        select(IdentidadeOAuth).where(
            IdentidadeOAuth.provedor == provedor, IdentidadeOAuth.id_externo == id_externo
        )
    ).scalar_one_or_none()
    if identidade is not None:
        return identidade.usuario

    if not email_verificado:
        raise EmailNaoVerificado

    email = email.strip().lower()
    usuario = _por_email(db, email)
    if usuario is None:
        base = username_sugerido or email.split("@")[0]
        usuario = Usuario(
            email=email,
            username=_username_livre(db, base),
            nome_exibicao=(nome or base)[:120],
            avatar_url=avatar_url,
        )
        db.add(usuario)
    elif any(identidade.provedor == provedor for identidade in usuario.identidades):
        raise ProvedorJaVinculado
    elif usuario.avatar_url is None:
        usuario.avatar_url = avatar_url

    usuario.identidades.append(IdentidadeOAuth(provedor=provedor, id_externo=id_externo))
    try:
        db.commit()
    except IntegrityError:
        # Duas abas concluindo o mesmo login ao mesmo tempo: a outra venceu, e o
        # vínculo que ela gravou é o que vale.
        db.rollback()
        identidade = db.execute(
            select(IdentidadeOAuth).where(
                IdentidadeOAuth.provedor == provedor, IdentidadeOAuth.id_externo == id_externo
            )
        ).scalar_one_or_none()
        if identidade is None:
            raise
        return identidade.usuario
    return usuario


# --- redefinição de senha -----------------------------------------------------


def solicitar_redefinicao(email: str) -> None:
    """Gera o link de "Esqueceu a senha?" se o e-mail tiver conta.

    Roda em background, depois da resposta: assim o 202 sai no mesmo tempo com
    e sem conta, e a rota não serve para descobrir quem está cadastrado. Por
    isso também abre a própria sessão do banco, em vez de receber a do request.
    """
    with SessionLocal() as db:
        usuario = _por_email(db, email)
        if usuario is None:
            return
        usuario_id = usuario.id

    token = secrets.token_urlsafe(32)
    gravado = executar(
        lambda r: r.setex(_chave_redefinicao(token), settings.redefinir_senha_ttl, str(usuario_id)),
        padrao=False,
    )
    if not gravado:
        logger.error("Redis fora: link de redefinição de senha não foi gerado")
        return

    # Provisório: não há serviço de e-mail ainda, então o link vai para o log.
    # WARNING para aparecer no log padrão do uvicorn, que não mostra INFO de
    # loggers da aplicação.
    logger.warning(
        "Link de redefinição de senha (usuário %s): %s/redefinir-senha?token=%s",
        usuario_id,
        settings.frontend_origin,
        token,
    )


def redefinir_senha(db: Session, token: str, nova_senha: str) -> None:
    # `GETDEL`: ler e apagar na mesma operação é o que garante o uso único,
    # mesmo com dois envios simultâneos do mesmo link.
    dono = executar(lambda r: r.getdel(_chave_redefinicao(token)), padrao=None)
    usuario = db.get(Usuario, int(dono)) if dono is not None else None
    if usuario is None:
        raise LinkInvalido

    usuario.senha_hash = seguranca.gerar_hash(nova_senha)
    db.commit()

    # Quem pediu a troca pode estar fugindo de alguém logado na conta.
    sessoes.revogar_todas(usuario.id)


def _chave_redefinicao(token: str) -> str:
    # Guarda o hash, não o token: quem ler o Redis não sai com um link que funciona.
    return chave("senha", "redefinir", hashlib.sha256(token.encode()).hexdigest())


# --- apoio --------------------------------------------------------------------


def _por_email(db: Session, email: str) -> Usuario | None:
    return db.execute(
        select(Usuario).where(func.lower(Usuario.email) == email.strip().lower())
    ).scalar_one_or_none()


def _username_em_uso(db: Session, username: str) -> bool:
    encontrado = db.execute(
        select(Usuario.id).where(func.lower(Usuario.username) == username.lower())
    ).first()
    return encontrado is not None


def _username_livre(db: Session, base: str) -> str:
    """Username para conta nova de OAuth, derivado do login do provedor ou do e-mail.

    Mesmo formato do cadastro (letras, números e `_`, de 3 a 50), com sufixo
    numérico se já estiver em uso.
    """
    limpo = re.sub(r"[^a-zA-Z0-9_]", "_", base).strip("_")[:40] or "aluno"
    limpo = limpo.ljust(3, "_")

    candidato = limpo
    for sufixo in range(2, 100):
        if not _username_em_uso(db, candidato):
            return candidato
        candidato = f"{limpo}_{sufixo}"
    return f"{limpo}_{secrets.token_hex(4)}"
