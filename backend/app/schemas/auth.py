"""Contrato das rotas de autenticação (telas 5 e 6)."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.seguranca import MAXIMO_BYTES_SENHA

__all__ = [
    "EsqueciSenha",
    "ExclusaoConta",
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
    # Checkbox "Aceito os termos de uso e a política de privacidade" da tela 6.
    # Obrigatório e verdadeiro: sem aceite não há base legal para guardar nada.
    # `validate_default`: sem ele, não mandar o campo pularia o validador.
    aceite_termos: bool = Field(default=False, validate_default=True)
    # Opcional: o formulário da tela 6 não pede. Sem ele, vale o username.
    nome_exibicao: str | None = Field(default=None, min_length=2, max_length=120)
    # Opcional: sem ele, sai do e-mail. Mesmos caracteres que o username gerado
    # a partir do e-mail pode ter.
    username: str | None = Field(
        default=None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9._-]+$"
    )

    @field_validator("aceite_termos")
    @classmethod
    def _aceitou(cls, valor: bool) -> bool:
        if not valor:
            raise ValueError("É preciso aceitar os termos de uso e a política de privacidade")
        return valor


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
    # Diz ao frontend se pedir a senha faz sentido (ex.: para excluir a conta).
    tem_senha: bool = False


class Sessao(BaseModel):
    access_token: str
    refresh_token: str
    # Fixo em "bearer" para o cliente montar o header sem adivinhar.
    token_type: str = "bearer"
    # Segundos de validade do access token, para o frontend renovar antes.
    expira_em: int
    usuario: UsuarioAutenticado
    # Recado para o frontend mostrar, como "a exclusão da sua conta foi
    # cancelada" quando o aluno entra durante o prazo de exclusão.
    aviso: str | None = None


class Renovacao(BaseModel):
    """Corpo do refresh e do logout: os dois recebem o refresh token."""

    refresh_token: str


class EsqueciSenha(BaseModel):
    email: EmailStr


class RedefinirSenha(_ComSenhaNova):
    token: str


class ExclusaoConta(BaseModel):
    """Corpo do `DELETE /usuarios/me`."""

    # O aluno digita "EXCLUIR": confirmação explícita, que um clique sem querer
    # ou um script não dão.
    confirmacao: str
    # Obrigatória para conta com senha; conta só de OAuth manda nula.
    senha: str | None = None
