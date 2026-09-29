"""Clientes OAuth2 do GitHub e do Google (Authlib).

Só é registrado o provedor que tem credenciais no ambiente. Sem elas, a rota do
botão responde 503 em vez de a API deixar de subir — dá para desenvolver o resto
sem criar os dois apps OAuth.

O `state` do OAuth (a proteção contra CSRF no callback) fica na sessão do
Starlette, um cookie assinado que só existe durante o vaivém com o provedor. Por
isso o `SessionMiddleware` em `app/main.py`.
"""

from authlib.integrations.starlette_client import OAuth, StarletteOAuth2App

from app.core.config import settings
from app.models import ProvedorOAuth

oauth = OAuth()

if settings.github_client_id:
    oauth.register(
        name=ProvedorOAuth.github.value,
        client_id=settings.github_client_id,
        client_secret=settings.github_client_secret,
        authorize_url="https://github.com/login/oauth/authorize",
        access_token_url="https://github.com/login/oauth/access_token",
        api_base_url="https://api.github.com/",
        # `user:email` é o que libera `/user/emails`: o perfil não traz o e-mail
        # quando o aluno deixa ele privado no GitHub.
        client_kwargs={"scope": "read:user user:email"},
    )

if settings.google_client_id:
    oauth.register(
        name=ProvedorOAuth.google.value,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        # OpenID Connect: endpoints e chaves vêm do discovery, e o id_token já
        # chega validado com o e-mail e o `email_verified` dentro.
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def cliente(provedor: ProvedorOAuth) -> StarletteOAuth2App | None:
    """Cliente do provedor, ou None se ele não estiver configurado."""
    return oauth.create_client(provedor.value)
