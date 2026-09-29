"""Contrato das rotas de autenticação (telas 5 e 6)."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.seguranca import MAXIMO_BYTES_SENHA

__all__ = [
    "EsqueciSenha",
    "Login",
    "RedefinirSenha",
    "Registro",
    "Renovacao",
    "Sessao",
    "UsuarioAutenticado",
]

# Oito caracteres é o piso; o teto vem do bcrypt, que ignora o que passa de 72
# bytes. Em acentuado um caractere ocupa dois bytes, então o limite em
# caracteres é conservador e a checagem em bytes fica no validador.
SenhaNova = Field(min_length=8, max_length=MAXIMO_BYTES_SENHA)


class _ComSenhaNova(BaseModel):
    senha: str = SenhaNova

    @field_validator("senha")
    @classmethod
    def _cabe_no_bcrypt(cls, valor: str) -> str:
        if len(valor.encode("utf-8")) > MAXIMO_BYTES_SENHA:
            raise ValueError(f"A senha passa de {MAXIMO_BYTES_SENHA} bytes")
        return valor


class Registro(_ComSenhaNova):
    email: EmailStr
    nome_exibicao: str = Field(min_length=2, max_length=120)
    # Opcional: sem ele, sai do e-mail.
    username: str | None = Field(default=None, min_length=3, max_length=50)


class Login(BaseModel):
    email: EmailStr
    senha: str
    # "Manter-se conectado" da tela 5: só alonga o refresh token.
    lembrar: bool = False


class UsuarioAutenticado(BaseModel):
    """O aluno como as telas privadas o veem."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    username: str
    nome_exibicao: str
    avatar_url: str | None = None
    xp_total: int = 0


class Sessao(BaseModel):
    access_token: str
    refresh_token: str
    # Fixo em "bearer" para o cliente montar o header sem adivinhar.
    token_type: str = "bearer"
    # Segundos de validade do access token, para o frontend renovar antes.
    expira_em: int
    usuario: UsuarioAutenticado


class Renovacao(BaseModel):
    """Corpo do refresh e do logout: os dois recebem o refresh token."""

    refresh_token: str


class EsqueciSenha(BaseModel):
    email: EmailStr


class RedefinirSenha(_ComSenhaNova):
    token: str
