"""Contrato das rotas de `/auth` (telas 5 e 6)."""

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, EmailStr, Field

from app.schemas.usuario import Usuario


def _normalizar_email(email: str) -> str:
    # E-mail é comparado sem diferenciar maiúsculas: `Ana@x.com` e `ana@x.com`
    # são a mesma conta.
    return email.strip().lower()


def _caber_no_bcrypt(senha: str) -> str:
    # O bcrypt ignora o que passa de 72 bytes (e a versão 5 recusa). O limite é
    # em bytes, não em caracteres: acento ocupa dois.
    if len(senha.encode()) > 72:
        raise ValueError("A senha pode ter no máximo 72 bytes.")
    return senha


Email = Annotated[EmailStr, AfterValidator(_normalizar_email)]

# Mesmas regras do formulário do frontend (`lib/validation/auth.ts`).
NovaSenha = Annotated[str, Field(min_length=8), AfterValidator(_caber_no_bcrypt)]
Username = Annotated[str, Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")]


class RegistroEntrada(BaseModel):
    username: Username
    email: Email
    senha: NovaSenha
    manter_conectado: bool = False


class LoginEntrada(BaseModel):
    email: Email
    # Sem as regras de senha nova: no login, senha fora do padrão é só senha
    # errada, e o 401 tem que ser o mesmo de qualquer outra.
    senha: str = Field(max_length=1024)
    manter_conectado: bool = False


class RefreshEntrada(BaseModel):
    refresh_token: str


class EsqueciSenhaEntrada(BaseModel):
    email: Email


class RedefinirSenhaEntrada(BaseModel):
    token: str
    nova_senha: NovaSenha


class Sessao(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    # Segundos até o access token vencer, para o frontend agendar o refresh.
    expira_em: int
    usuario: Usuario
