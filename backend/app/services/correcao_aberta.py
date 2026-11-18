"""Correção da resposta aberta pela IA (#22).

Separada de `submissoes` porque é a única correção que depende de rede: as
outras são regra pura. Quem chama trata a falha (IA fora do ar, lenta ou com
resposta fora do formato) como "não deu para corrigir agora" e guarda a
resposta em análise, sem pagar XP e sem prender o aluno.
"""

import anyio

from app.ia import ProvedorIA, para
from app.ia.skills import corrigir_resposta

# O aluno está olhando para o botão "Verificar": passou disso, a resposta fica
# em análise e ele segue. O provedor tem o próprio timeout, mais longo, que é o
# do chat.
TEMPO_MAXIMO_SEGUNDOS = 25


async def corrigir(
    provedor: ProvedorIA, *, enunciado: str, referencia: str, resposta: str
) -> corrigir_resposta.Resposta:
    """O veredito da IA. Levanta `IAIndisponivel`, `SaidaInvalida` ou `TimeoutError`."""
    pedacos: list[str] = []
    with anyio.fail_after(TEMPO_MAXIMO_SEGUNDOS):
        async for pedaco in para(provedor, "correcao").gerar(
            corrigir_resposta.mensagens(enunciado, referencia, resposta),
            max_tokens=corrigir_resposta.MAXIMO_DE_TOKENS,
            formato=corrigir_resposta.FORMATO,
        ):
            pedacos.append(pedaco)
    return corrigir_resposta.ler_resposta("".join(pedacos))
