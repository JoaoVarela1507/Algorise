"""Skill que resume o começo de uma conversa do chat (#33).

O tutor recebe só as últimas `CHAT_JANELA_HISTORICO` mensagens. O que fica de
fora não some: vira um resumo curto, que vai antes delas. A cada vez que mais
mensagens saem da janela, o resumo anterior e essas mensagens viram um resumo
novo, então o custo não cresce com o tamanho da conversa.
"""

from collections.abc import Sequence

from app.ia.base import MensagemIA

MAXIMO_DE_TOKENS = 400
# Caracteres de cada mensagem que entram no pedido: uma resposta longa do tutor
# não precisa ir inteira para virar duas linhas de resumo.
TRECHO_DA_MENSAGEM = 1500

PROMPT = """\
Você resume conversas entre um aluno de programação e um tutor, para o tutor \
lembrar do que já foi falado.

Escreva em português, em até seis frases curtas, só o que importa para continuar \
ajudando: as dúvidas do aluno, o que já foi explicado, o código ou o exercício em \
questão e o que ficou pendente. Não invente nada que não esteja na conversa e \
não se dirija ao aluno."""


def mensagens(resumo_anterior: str | None, falas: Sequence[tuple[str, str]]) -> list[MensagemIA]:
    """`falas` são pares (`aluno` ou `tutor`, texto), da mais antiga para a mais nova."""
    partes = []
    if resumo_anterior:
        partes.append(f"Resumo do que veio antes:\n{resumo_anterior}")
    partes.append(
        "Continuação da conversa:\n"
        + "\n".join(f"{quem}: {texto[:TRECHO_DA_MENSAGEM]}" for quem, texto in falas)
    )
    return [MensagemIA("system", PROMPT), MensagemIA("user", "\n\n".join(partes))]
