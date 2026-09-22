"""Login social: clientes do GitHub e do Google, e o vínculo com a conta local.

O que os dois provedores têm em comum é o fim do fluxo: um `perfil` com id,
e-mail e nome, que vira conta nova ou vínculo com uma conta já existente. O que
muda é como esse perfil é obtido — o Google entrega no `id_token`, o GitHub exige
uma chamada a mais para o e-mail.

O vínculo é pelo par (provedor, id no provedor), não pelo e-mail: e-mail do
GitHub o aluno troca quando quiser, o id não muda. O e-mail entra só para achar
uma conta local já existente na primeira vez.
"""

import logging
from dataclasses import dataclass

from authlib.integrations.starlette_client import OAuth
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ContaOAuth, Usuario
from app.services.auth import username_livre

logger = logging.getLogger(__name__)

GITHUB = "github"
GOOGLE = "google"
PROVEDORES = (GITHUB, GOOGLE)


class ProvedorIndisponivel(Exception):
    """Provedor sem credencial configurada, ou nome de provedor desconhecido."""


class PerfilIncompleto(Exception):
    """O provedor não deu um e-mail verificado, e sem e-mail não dá para criar conta."""


@dataclass(frozen=True)
class Perfil:
    """O mínimo que precisamos de um provedor, já normalizado."""

    provedor: str
    provedor_id: str
    email: str
    nome: str
    avatar_url: str | None = None


oauth = OAuth()

oauth.register(
    name=GITHUB,
    client_id=settings.github_client_id,
    client_secret=settings.github_client_secret,
    access_token_url="https://github.com/login/oauth/access_token",
    authorize_url="https://github.com/login/oauth/authorize",
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "read:user user:email"},
)

oauth.register(
    name=GOOGLE,
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    # O documento de descoberta evita fixar endpoints que o Google pode mudar.
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


def cliente(provedor: str):
    """Cliente configurado do provedor, ou erro se falta credencial.

    A checagem existe para o ambiente sem `GITHUB_CLIENT_ID` responder 503 com
    uma mensagem clara, em vez de redirecionar o aluno para uma tela de erro do
    provedor.
    """
    if provedor not in PROVEDORES:
        raise ProvedorIndisponivel(provedor)

    credenciais = {
        GITHUB: (settings.github_client_id, settings.github_client_secret),
        GOOGLE: (settings.google_client_id, settings.google_client_secret),
    }[provedor]

    if not all(credenciais):
        raise ProvedorIndisponivel(provedor)

    return getattr(oauth, provedor)


async def perfil_do_github(token: dict) -> Perfil:
    """Perfil do GitHub, com a busca extra do e-mail.

    O `/user` só traz o e-mail quando o aluno o deixou público, então o e-mail
    verificado vem de `/user/emails`. Sem ele não dá para vincular a conta.
    """
    api = getattr(oauth, GITHUB)
    dados = (await api.get("user", token=token)).json()

    email = dados.get("email")
    if not email:
        emails = (await api.get("user/emails", token=token)).json()
        email = next(
            (
                item["email"]
                for item in emails
                if item.get("primary") and item.get("verified") and item.get("email")
            ),
            None,
        )

    if not email:
        raise PerfilIncompleto(GITHUB)

    return Perfil(
        provedor=GITHUB,
        provedor_id=str(dados["id"]),
        email=email.lower(),
        nome=dados.get("name") or dados.get("login") or email.split("@")[0],
        avatar_url=dados.get("avatar_url"),
    )


def perfil_do_google(token: dict) -> Perfil:
    """Perfil do Google, que já vem no `id_token` validado pelo Authlib."""
    dados = token.get("userinfo") or {}

    # `email_verified` falso quer dizer que o próprio Google não confirmou o
    # e-mail; aceitar isso permitiria assumir a conta de outra pessoa.
    if not dados.get("email") or not dados.get("email_verified"):
        raise PerfilIncompleto(GOOGLE)

    return Perfil(
        provedor=GOOGLE,
        provedor_id=str(dados["sub"]),
        email=str(dados["email"]).lower(),
        nome=dados.get("name") or str(dados["email"]).split("@")[0],
        avatar_url=dados.get("picture"),
    )


def vincular_ou_criar(db: Session, perfil: Perfil) -> Usuario:
    """Resolve o perfil do provedor numa conta do Algorise.

    Três caminhos: já existe o vínculo, existe conta com o mesmo e-mail (aí o
    vínculo é criado), ou não existe nada (aí a conta nasce sem senha — o aluno
    entra sempre pelo provedor, ou define senha depois pela recuperação).
    """
    vinculo = db.execute(
        select(ContaOAuth).where(
            ContaOAuth.provedor == perfil.provedor,
            ContaOAuth.provedor_id == perfil.provedor_id,
        )
    ).scalar_one_or_none()

    if vinculo is not None:
        return vinculo.usuario

    usuario = db.execute(select(Usuario).where(Usuario.email == perfil.email)).scalar_one_or_none()

    if usuario is None:
        usuario = Usuario(
            email=perfil.email,
            username=username_livre(db, perfil.email.split("@")[0]),
            nome_exibicao=perfil.nome,
            avatar_url=perfil.avatar_url,
            senha_hash=None,
        )
        db.add(usuario)
        db.flush()
    elif usuario.avatar_url is None:
        usuario.avatar_url = perfil.avatar_url

    db.add(
        ContaOAuth(
            usuario_id=usuario.id,
            provedor=perfil.provedor,
            provedor_id=perfil.provedor_id,
            email=perfil.email,
        )
    )
    db.commit()
    return usuario
