"""Política de senha nova (cadastro e redefinição), no estilo do NIST 800-63B.

O que o NIST recomenda, e o que fica de fora de propósito:

- comprimento mínimo (8) e máximo (72 bytes, o teto do bcrypt) — no schema;
- recusar senha comum, sequência óbvia e senha que contém o e-mail ou o
  username — aqui;
- **não** exigir símbolo, número ou maiúscula. Regra de composição empurra o
  aluno para `Senha@123`, que passa em toda regra e cai no primeiro dicionário.

Vale só para senha nova: no login, senha fora da política é só senha errada.
"""

from itertools import pairwise

# Senhas que aparecem no topo dos vazamentos, em português e em inglês, e as
# óbvias para este app.
SENHAS_COMUNS = frozenset(
    {
        "12345678",
        "123456789",
        "1234567890",
        "0123456789",
        "11111111",
        "00000000",
        "12341234",
        "12121212",
        "87654321",
        "123123123",
        "11223344",
        "1q2w3e4r",
        "1q2w3e4r5t",
        "q1w2e3r4",
        "zaq12wsx",
        "qazwsxedc",
        "qwertyui",
        "qwerty123",
        "qwerty12",
        "asdfghjk",
        "asdf1234",
        "abcd1234",
        "abc12345",
        "abcdefgh",
        "password",
        "passw0rd",
        "iloveyou",
        "sunshine",
        "princess",
        "football",
        "baseball",
        "welcome1",
        "letmein1",
        "trustno1",
        "superman",
        "starwars",
        "whatever",
        "computer",
        "internet",
        "senha123",
        "senha1234",
        "senha12345",
        "senhasenha",
        "minhasenha",
        "mudar123",
        "mudar1234",
        "trocar123",
        "admin123",
        "administrador",
        "brasil123",
        "flamengo",
        "corinthians",
        "palmeiras",
        "saopaulo",
        "vasco123",
        "gremio123",
        "cruzeiro",
        "botafogo",
        "fluminense",
        "teamo123",
        "eusouodono",
        "algorise",
        "aluno123",
        "estudante",
        "faculdade",
        "universidade",
        "programacao",
        "programador",
        "python123",
        "javascript",
        # Raízes curtas: sozinhas o schema já recusa, mas com enfeite no fim
        # (`Senha@123`, `admin2024`) chegam aqui pela comparação da raiz.
        "senha",
        "admin",
        "aluno",
        "teamo",
        "mudar",
        "trocar",
        "brasil",
        "python",
        "qwerty",
    }
)

# Pedaços do e-mail ou do username menores que isso não contam: barrar "ana"
# dentro da senha de quem se chama Ana recusaria senhas boas à toa.
_TAMANHO_MINIMO_DE_TRECHO = 4


def problema_da_senha(senha: str, *, email: str = "", username: str = "") -> str | None:
    """Motivo para recusar a senha, em português, ou None se ela serve."""
    normalizada = senha.strip().lower()

    # `Flamengo2024!` é `flamengo` com enfeite: compara também sem o que vem
    # depois do trecho alfabético.
    #
    # Sem regex de propósito: `[\d\W_]+$` sobre entrada do usuário é ReDoS
    # polinomial — numa senha de muitos dígitos, o motor tenta casar a partir de
    # cada posição. O corte abaixo é linear e a senha vem do cadastro.
    raiz = _sem_enfeite_no_fim(normalizada)
    if normalizada in SENHAS_COMUNS or raiz in SENHAS_COMUNS:
        return "Essa senha é muito comum. Escolha uma mais difícil de adivinhar."

    if len(set(normalizada)) <= 2:
        return "A senha não pode repetir só um ou dois caracteres."

    if _sequencia(normalizada):
        return "A senha não pode ser uma sequência, como 12345678 ou abcdefgh."

    trechos = {email.split("@")[0].lower(), username.lower()}
    if any(len(t) >= _TAMANHO_MINIMO_DE_TRECHO and t in normalizada for t in trechos):
        return "A senha não pode conter o seu e-mail ou nome de usuário."

    return None


def _sem_enfeite_no_fim(texto: str) -> str:
    r"""Tira do fim tudo que não for letra: `flamengo2024!` -> `flamengo`.

    `isalpha()` é unicode como o `\w` do `re`, então acento continua contando
    como letra e `coração` não vira `cora`.
    """
    fim = len(texto)
    while fim and not texto[fim - 1].isalpha():
        fim -= 1
    return texto[:fim]


def _sequencia(texto: str) -> bool:
    """Sobe ou desce de um em um do começo ao fim: `12345678`, `hgfedcba`."""
    passos = {ord(b) - ord(a) for a, b in pairwise(texto)}
    return passos in ({1}, {-1})
