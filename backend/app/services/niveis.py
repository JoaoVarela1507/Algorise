"""Curva de níveis e as regras de pontuação, num lugar só.

A curva é **quadrática**: o nível N começa em `BASE * (N-1)²`. Isso dá degraus
que crescem sem explodir — do 1 para o 2 são 50 XP, do 9 para o 10 são 750 —, o
que mantém o começo rápido (o aluno vê progresso na primeira sessão) sem que o
nível 20 vire um número que qualquer um alcança numa tarde.

Por que fórmula e não tabela: tabela precisa de manutenção e acaba desatualizada
em relação ao front. Com fórmula, `nivel_de` e `faixa_do_nivel` são inversas uma
da outra por construção, e o teste compara as duas.

## Quanto vale cada coisa

| Ação | XP | Onde está |
| --- | --- | --- |
| acertar uma atividade | o `xp` da atividade (10 a 20 no seed) | `services/submissoes.py` |
| fechar um passo | `XP_POR_PASSO` | `services/submissoes.py` |

XP sai **uma vez** por atividade e uma vez por passo: repetir não paga de novo.
O teto por janela de tempo está em `services/gamificacao.py`.
"""

from math import isqrt

# XP do nível 1 para o 2. Os degraus seguintes saem da curva.
BASE = 50


def nivel_de(xp: int) -> int:
    """Nível do aluno. Começa em 1, e XP negativo não existe."""
    if xp < BASE:
        return 1
    # Inversa de `xp_do_nivel`: N = 1 + raiz(xp / BASE), por baixo.
    return 1 + isqrt(xp // BASE)


def xp_do_nivel(nivel: int) -> int:
    """XP acumulado necessário para **entrar** neste nível."""
    return BASE * (max(nivel, 1) - 1) ** 2


def faixa_do_nivel(xp: int) -> tuple[int, int, int]:
    """`(nivel, xp_dentro_do_nivel, xp_que_falta_para_o_proximo)`.

    É o que a barra de progresso da tela 16 precisa: onde está dentro do nível e
    quanto falta, sem o cliente precisar conhecer a curva.
    """
    nivel = nivel_de(xp)
    inicio = xp_do_nivel(nivel)
    proximo = xp_do_nivel(nivel + 1)

    return nivel, xp - inicio, proximo - xp
