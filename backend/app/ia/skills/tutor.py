"""Skill do tutor do chat (telas 21 a 23, #11).

Tom de quem ensina iniciantes, em português, com o contexto do aluno no prompt
de sistema. Só entra o que o aluno informou: sem curso, o prompt não diz curso
nenhum, e o modelo não tem de onde inventar um.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.ia.base import MensagemIA
from app.models.enums import ModoResposta, NivelExperiencia

# Teto de tokens da resposta por modo. O "rápido" é para tirar uma dúvida
# pontual; o "detalhado" leva exemplo e exercício, e precisa de espaço.
MAXIMO_DE_TOKENS = {
    ModoResposta.rapido: 300,
    ModoResposta.medio: 800,
    ModoResposta.detalhado: 5000,
}

INSTRUCAO_DO_MODO = {
    ModoResposta.rapido: "Responda em no máximo três frases, direto ao ponto.",
    ModoResposta.medio: "Responda de forma objetiva, com um exemplo curto se ajudar.",
    ModoResposta.detalhado: (
        "Explique passo a passo, com um exemplo comentado e, no fim, um exercício curto "
        "para o aluno praticar."
    ),
}

DESCRICAO_DO_NIVEL = {
    NivelExperiencia.baixo: "está começando a programar agora: evite jargão sem explicar",
    NivelExperiencia.medio: "já programa um pouco e conhece o básico",
    NivelExperiencia.alto: "já programa com segurança: pode ir mais fundo",
}

PROMPT = """\
Você é o tutor do Algorise, uma plataforma que ensina programação a estudantes \
de graduação por meio de trilhas de estudo.

Como responder:
- Sempre em português do Brasil, com tom acolhedor de quem ensina iniciantes.
- Explique o porquê, não só o como. Prefira exemplos pequenos em Python, em \
blocos de código Markdown com a linguagem indicada.
- Se o aluno pedir a resposta pronta de um exercício, guie com dicas e perguntas \
antes de entregar a solução.
- Se não souber algo, ou se a pergunta for sobre o curso ou a ementa do aluno e \
você não tiver essa informação, diga que não sabe. Não invente.
- Se o assunto não tiver relação com programação, computação ou estudos, recuse \
com gentileza e traga a conversa de volta."""


@dataclass(frozen=True)
class Aluno:
    """O que o tutor sabe do aluno, já em texto. Campo vazio fica fora do prompt."""

    nivel: NivelExperiencia
    curso: str | None = None
    instituicao: str | None = None
    periodo: int | None = None
    trilha: str | None = None
    disciplina: str | None = None
    modulo: str | None = None


def mensagens(
    aluno: Aluno, modo: ModoResposta, historico: Sequence[MensagemIA], pergunta: str
) -> list[MensagemIA]:
    """Instrução, histórico da conversa e a pergunta nova, na ordem do modelo."""
    return [MensagemIA("system", instrucao(aluno, modo)), *historico, MensagemIA("user", pergunta)]


def max_tokens(modo: ModoResposta) -> int:
    return MAXIMO_DE_TOKENS[modo]


def instrucao(aluno: Aluno, modo: ModoResposta) -> str:
    sobre = [f"- Nível de experiência: {DESCRICAO_DO_NIVEL[aluno.nivel]}."]

    periodo = f", no {aluno.periodo}º período" if aluno.periodo else ""
    if aluno.curso and aluno.instituicao:
        sobre.append(f"- Cursa {aluno.curso} na {aluno.instituicao}{periodo}.")
    elif aluno.curso:
        sobre.append(f"- Cursa {aluno.curso}{periodo}.")
    elif aluno.instituicao:
        sobre.append(f"- Estuda na {aluno.instituicao}{periodo}.")

    if aluno.trilha:
        disciplina = f" ({aluno.disciplina})" if aluno.disciplina else ""
        modulo = f', no módulo "{aluno.modulo}"' if aluno.modulo else ""
        sobre.append(f'- Está na trilha "{aluno.trilha}"{disciplina}{modulo}.')

    return "\n\n".join([PROMPT, "Sobre o aluno:\n" + "\n".join(sobre), INSTRUCAO_DO_MODO[modo]])
