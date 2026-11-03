"""Seed da trilha "Introdução Python" — a trilha do protótipo.

Idempotente: identifica a trilha pelo slug, os módulos pela ordem e as
atividades pela ordem dentro do módulo, então rodar duas vezes atualiza em vez
de duplicar.

Cada módulo tem 7 atividades, misturando os tipos, e termina fechando o
assunto: o aluno sai do passo tendo visto o conceito de mais de um jeito.
"""

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Atividade, CasoDeTeste, Modulo, Trilha
from app.models.enums import TipoAtividade

SLUG = "introducao-python"


def _lista(*itens: str) -> str:
    """O gabarito da ordenação e da lacuna: uma lista JSON (ver `Atividade.resposta_esperada`)."""
    return json.dumps(list(itens), ensure_ascii=False)


def _escolha(
    ordem: int,
    enunciado: str,
    opcoes: list[str],
    certa: str,
    *,
    dica: str | None = None,
    codigo: str | None = None,
) -> dict:
    assert certa in opcoes, f"a alternativa certa precisa estar nas opções: {enunciado}"
    return {
        "ordem": ordem,
        "tipo": TipoAtividade.multipla_escolha,
        "enunciado": enunciado,
        "opcoes": opcoes,
        "resposta_esperada": certa,
        "dica": dica,
        "codigo": codigo,
        "tempo_sugerido_segundos": 45,
        "xp": 10,
    }


def _lacuna(
    ordem: int,
    enunciado: str,
    codigo: str,
    respostas: list[str],
    *,
    banco: list[str] | None = None,
    dica: str | None = None,
) -> dict:
    assert codigo.count("___") == len(respostas), f"um gabarito por buraco: {enunciado}"
    return {
        "ordem": ordem,
        "tipo": TipoAtividade.preencher_lacuna,
        "enunciado": enunciado,
        "codigo": codigo,
        "opcoes": banco,
        "resposta_esperada": _lista(*respostas),
        "dica": dica,
        "tempo_sugerido_segundos": 60,
        "xp": 10,
    }


def _ordenar(
    ordem: int,
    enunciado: str,
    embaralhadas: list[str],
    certas: list[str],
    *,
    dica: str | None = None,
) -> dict:
    assert sorted(embaralhadas) == sorted(certas), f"as mesmas linhas nas duas listas: {enunciado}"
    assert embaralhadas != certas, f"a tela não pode já vir na ordem certa: {enunciado}"
    return {
        "ordem": ordem,
        "tipo": TipoAtividade.ordenacao,
        "enunciado": enunciado,
        "opcoes": embaralhadas,
        "resposta_esperada": _lista(*certas),
        "dica": dica,
        "tempo_sugerido_segundos": 90,
        "xp": 15,
    }


def _aberta(ordem: int, enunciado: str, esperada: str, *, dica: str | None = None) -> dict:
    return {
        "ordem": ordem,
        "tipo": TipoAtividade.resposta_aberta,
        "enunciado": enunciado,
        "resposta_esperada": esperada,
        "dica": dica,
        "tempo_sugerido_segundos": 120,
        "xp": 20,
    }


MODULOS: list[dict] = [
    {
        "ordem": 1,
        "titulo": "Iniciando no Python",
        "descricao": "Instale o Python e confirme que está tudo certo pelo terminal.",
        "video_url": "https://www.youtube.com/watch?v=S9uPNppGsGo",
        "atividades": [
            {
                "ordem": 1,
                "tipo": TipoAtividade.terminal,
                "enunciado": "No terminal do Windows, baixe a versão mais recente do Python",
                "dica": "Apresentado no vídeo, na parte de instalação",
                "comando_esperado": "winget install Python.Python.3.14",
                "saida_esperada": "Instalação concluída com êxito",
                "tempo_sugerido_segundos": 9,
                "xp": 10,
            },
            {
                "ordem": 2,
                "tipo": TipoAtividade.terminal,
                "enunciado": "No terminal do Windows, verifique a versão do Python",
                "dica": "Apresentado no vídeo, depois da instalação",
                "comando_esperado": "python --version",
                "saida_esperada": "Python 3.14.0",
                "tempo_sugerido_segundos": 9,
                "xp": 10,
            },
            _aberta(
                3,
                "Explique com suas palavras o que significa a FLAG (--version)",
                "Flags são parâmetros que modificam o comportamento de um comando. "
                "No exemplo --version, a flag faz o Python exibir a versão instalada.",
            ),
            _escolha(
                4,
                "O que é o Python?",
                [
                    "Um editor de texto",
                    "Uma linguagem de programação",
                    "Um sistema operacional",
                    "Um navegador de internet",
                ],
                "Uma linguagem de programação",
            ),
            _escolha(
                5,
                "Para que serve o comando python --version?",
                [
                    "Instalar o Python",
                    "Mostrar a versão do Python instalada",
                    "Atualizar o Windows",
                    "Abrir o editor de código",
                ],
                "Mostrar a versão do Python instalada",
            ),
            _lacuna(
                6,
                "Complete o comando que confere a versão do Python.",
                "python ___",
                ["--version"],
                banco=["--version", "--help", "install"],
            ),
            _ordenar(
                7,
                "Ordene os passos para começar a programar em Python.",
                [
                    "Escrever o primeiro programa",
                    "Instalar o Python com o winget",
                    "Abrir o terminal",
                    "Conferir a versão com python --version",
                ],
                [
                    "Abrir o terminal",
                    "Instalar o Python com o winget",
                    "Conferir a versão com python --version",
                    "Escrever o primeiro programa",
                ],
            ),
        ],
    },
    {
        "ordem": 2,
        "titulo": "Primeiro print()",
        "descricao": "Mostre mensagens na tela com a função print.",
        "atividades": [
            _escolha(
                1,
                "Qual linha mostra Olá, mundo! na tela?",
                [
                    'print("Olá, mundo!")',
                    'echo "Olá, mundo!"',
                    'mostrar("Olá, mundo!")',
                    'console.log("Olá, mundo!")',
                ],
                'print("Olá, mundo!")',
            ),
            _lacuna(
                2,
                "Complete o código para mostrar a mensagem de boas-vindas.",
                '___("Bem-vindo ao Algorise!")',
                ["print"],
                banco=["print", "input", "len"],
                dica="O texto vai entre aspas, dentro dos parênteses.",
            ),
            _escolha(
                3,
                "O que aparece na tela com print(2 + 3)?",
                ["5", "2 + 3", "23", "Dá erro"],
                "5",
                dica="Sem aspas, o Python faz a conta antes de mostrar.",
            ),
            _escolha(
                4,
                'O que aparece na tela com print("2 + 3")?',
                ["5", "2 + 3", "23", "Dá erro"],
                "2 + 3",
                dica="Entre aspas é texto: o Python mostra do jeito que está.",
            ),
            _lacuna(
                5,
                "Complete para mostrar o nome e a idade na mesma linha.",
                'print("Ana"___ 20)',
                [","],
                banco=[",", ";", "."],
                dica="É o que separa os valores dentro do print.",
            ),
            _ordenar(
                6,
                "Ordene para o programa cumprimentar, perguntar e se despedir.",
                ['print("Tchau!")', 'print("Olá!")', 'print("Tudo bem?")'],
                ['print("Olá!")', 'print("Tudo bem?")', 'print("Tchau!")'],
            ),
            _aberta(
                7,
                "Explique com suas palavras para que serve a função print.",
                "O print mostra na tela um texto ou o resultado de uma expressão, "
                "para quem está usando o programa ver.",
            ),
        ],
    },
    {
        "ordem": 3,
        "titulo": "Variáveis e tipos",
        "descricao": "Guarde valores e conheça int, float, str e bool.",
        "atividades": [
            _escolha(
                1,
                "Qual é o tipo do valor 3.14 em Python?",
                ["int", "float", "str", "bool"],
                "float",
            ),
            _lacuna(
                2,
                "Complete para guardar o nome e a idade.",
                'nome ___ "Ana"\nidade = ___',
                ["=", "20"],
                banco=["=", "==", "20", '"20"'],
                dica="A idade é um número inteiro, sem aspas.",
            ),
            _escolha(
                3,
                'Qual é o tipo de "42", escrito com aspas?',
                ["int", "float", "str", "bool"],
                "str",
                dica="As aspas transformam qualquer coisa em texto.",
            ),
            _escolha(
                4,
                "Qual destes é um nome de variável válido?",
                ["2nome", "nome_completo", "nome completo", "nome-completo"],
                "nome_completo",
                dica="Nome de variável não começa com número nem tem espaço ou hífen.",
            ),
            _lacuna(
                5,
                "Complete para descobrir o tipo da variável.",
                "idade = 20\nprint(___(idade))",
                ["type"],
                banco=["type", "int", "print"],
            ),
            _escolha(
                6,
                "Qual destes valores é do tipo bool?",
                ["True", '"True"', "1.0", "None"],
                "True",
                dica="bool só tem dois valores, e eles não levam aspas.",
            ),
            _ordenar(
                7,
                "Ordene para criar os pontos, somar mais 5 e mostrar o resultado.",
                ["print(pontos)", "pontos = 10", "pontos = pontos + 5"],
                ["pontos = 10", "pontos = pontos + 5", "print(pontos)"],
            ),
        ],
    },
    {
        "ordem": 4,
        "titulo": "Entrada de dados",
        "descricao": "Converse com quem usa o programa com input.",
        "atividades": [
            _escolha(
                1,
                "O que a função input() sempre devolve?",
                ["Um número inteiro", "Um texto (str)", "Um booleano", "Nada"],
                "Um texto (str)",
            ),
            _ordenar(
                2,
                "Ordene as linhas: pergunte a idade e diga quanto falta para 18.",
                ['print("Faltam", 18 - idade, "anos")', 'idade = int(input("Sua idade: "))'],
                ['idade = int(input("Sua idade: "))', 'print("Faltam", 18 - idade, "anos")'],
            ),
            _lacuna(
                3,
                "Complete para ler o nome de quem usa o programa.",
                'nome = ___("Seu nome: ")',
                ["input"],
                banco=["input", "print", "int"],
            ),
            _escolha(
                4,
                "Qual linha lê um número inteiro digitado pelo usuário?",
                [
                    'n = input("Número: ")',
                    'n = int(input("Número: "))',
                    'n = print("Número: ")',
                    'n = int("Número: ")',
                ],
                'n = int(input("Número: "))',
            ),
            _lacuna(
                5,
                "Complete para ler um preço com centavos.",
                'preco = ___(input("Preço: "))',
                ["float"],
                banco=["float", "int", "str"],
                dica="É o tipo dos números com parte decimal.",
            ),
            _escolha(
                6,
                "Com a = input() e o usuário digitando 5, o que print(a + a) mostra?",
                ["10", "55", "5", "Dá erro"],
                "55",
                dica="input devolve texto, e somar textos é juntar um no outro.",
            ),
            _aberta(
                7,
                "Explique por que é preciso usar int() para fazer contas com o que vem do input.",
                "O input devolve texto. Para fazer contas é preciso converter o texto em número "
                "com int() ou float(); senão o + junta os textos em vez de somar.",
            ),
        ],
    },
    {
        "ordem": 5,
        "titulo": "Operadores",
        "descricao": "Contas, comparações e lógica com and, or e not.",
        "atividades": [
            _escolha(
                1,
                "Quanto vale 7 // 2 em Python?",
                ["3.5", "3", "4", "1"],
                "3",
                dica="// é a divisão inteira: descarta a parte depois da vírgula.",
            ),
            _lacuna(
                2,
                "Complete para saber se o número é par.",
                "par = numero ___ 2 == 0",
                ["%"],
                banco=["%", "/", "//", "*"],
                dica="É o operador que devolve o resto da divisão.",
            ),
            _escolha(
                3,
                "Quanto vale 2 ** 3?",
                ["6", "8", "9", "5"],
                "8",
                dica="** é a potência: 2 multiplicado por ele mesmo 3 vezes.",
            ),
            _escolha(
                4,
                "Qual é o resultado de 10 > 3 and 2 > 5?",
                ["True", "False", "10", "Dá erro"],
                "False",
                dica="Com and, as duas comparações precisam ser verdadeiras.",
            ),
            _lacuna(
                5,
                "Complete para saber se a idade está entre 18 e 60.",
                "adulto = idade >= 18 ___ idade <= 60",
                ["and"],
                banco=["and", "or", "not"],
            ),
            _escolha(6, "Quanto vale 10 / 4?", ["2", "2.5", "3", "2.4"], "2.5"),
            _ordenar(
                7,
                "Ordene as linhas para calcular a média de duas notas.",
                ["print(media)", "n2 = 6", "media = (n1 + n2) / 2", "n1 = 8"],
                ["n1 = 8", "n2 = 6", "media = (n1 + n2) / 2", "print(media)"],
            ),
        ],
    },
    {
        "ordem": 6,
        "titulo": "Condicionais",
        "descricao": "Tome decisões com if, elif e else.",
        "atividades": [
            _ordenar(
                1,
                "Monte o programa que diz se a nota aprova (7 ou mais).",
                [
                    "else:",
                    'if nota >= 7:\n    print("Aprovado")',
                    "nota = 8",
                    '    print("Reprovado")',
                ],
                [
                    "nota = 8",
                    'if nota >= 7:\n    print("Aprovado")',
                    "else:",
                    '    print("Reprovado")',
                ],
            ),
            _escolha(
                2,
                "Com x = 5, o que o código abaixo mostra?",
                ["grande", "médio", "pequeno", "nada"],
                "médio",
                codigo=(
                    'if x > 10:\n    print("grande")\n'
                    'elif x > 3:\n    print("médio")\n'
                    'else:\n    print("pequeno")'
                ),
            ),
            _lacuna(
                3,
                "Complete a condição que confere se o número é negativo.",
                'if numero ___ 0:\n    print("negativo")',
                ["<"],
                banco=["<", ">", "=="],
            ),
            _escolha(
                4,
                "Qual palavra testa outra condição quando a do if não deu certo?",
                ["else", "elif", "then", "when"],
                "elif",
            ),
            _lacuna(
                5,
                "Complete o programa que diz se é maior ou menor de idade.",
                'if idade >= 18:\n    print("maior")\n___:\n    print("menor")',
                ["else"],
                banco=["else", "elif", "if"],
                dica="É o caminho de quando nenhuma condição deu certo; ele não tem condição.",
            ),
            _escolha(
                6,
                "O que o Python usa para marcar o que fica dentro do if?",
                [
                    "Chaves { }",
                    "Os espaços no começo da linha (indentação)",
                    "Ponto e vírgula no fim da linha",
                    "A palavra end",
                ],
                "Os espaços no começo da linha (indentação)",
            ),
            _aberta(
                7,
                "Explique quando usar elif em vez de vários if seguidos.",
                "O elif encadeia condições que se excluem: só a primeira verdadeira roda. "
                "Com vários if seguidos, todas as condições são testadas e mais de uma pode rodar.",
            ),
        ],
    },
    {
        "ordem": 7,
        "titulo": "Listas",
        "descricao": "Guarde vários valores e percorra-os.",
        "atividades": [
            _escolha(
                1,
                'Em frutas = ["maçã", "banana", "uva"], o que é frutas[1]?',
                ['"maçã"', '"banana"', '"uva"', "Dá erro"],
                '"banana"',
                dica="A contagem das posições começa do zero.",
            ),
            _lacuna(
                2,
                "Complete para colocar um gasto no fim da lista.",
                "gastos = [12.5, 30]\ngastos.___(8)",
                ["append"],
                banco=["append", "add", "push", "insert"],
            ),
            _escolha(3, "Quanto vale len([4, 8, 15])?", ["2", "3", "15", "27"], "3"),
            _lacuna(
                4,
                "Complete para pegar o último item da lista.",
                "ultimo = gastos[___]",
                ["-1"],
                banco=["-1", "0", "1"],
                dica="Posições negativas contam de trás para frente.",
            ),
            _escolha(
                5,
                'Depois de nomes = ["Ana"] e nomes.append("Bia"), como fica a lista?',
                ['["Ana"]', '["Bia", "Ana"]', '["Ana", "Bia"]', '"AnaBia"'],
                '["Ana", "Bia"]',
            ),
            _ordenar(
                6,
                "Ordene para criar a lista, adicionar um gasto e mostrar o total.",
                ["print(sum(gastos))", "gastos.append(20)", "gastos = [10, 5]"],
                ["gastos = [10, 5]", "gastos.append(20)", "print(sum(gastos))"],
            ),
            _lacuna(
                7,
                "Complete para saber se uva está na lista de frutas.",
                'tem_uva = "uva" ___ frutas',
                ["in"],
                banco=["in", "is", "=="],
            ),
        ],
    },
    {
        "ordem": 8,
        "titulo": "Repetição",
        "descricao": "Repita tarefas com for e while.",
        "atividades": [
            _escolha(
                1,
                "Quantas vezes o print roda em for i in range(3)?",
                ["2", "3", "4", "Infinitas"],
                "3",
            ),
            _ordenar(
                2,
                "Monte o programa que soma os gastos da lista.",
                ["    total = total + gasto", "print(total)", "total = 0", "for gasto in gastos:"],
                ["total = 0", "for gasto in gastos:", "    total = total + gasto", "print(total)"],
            ),
            _escolha(
                3,
                "Quais números range(1, 4) gera?",
                ["1, 2, 3, 4", "1, 2, 3", "0, 1, 2, 3", "2, 3, 4"],
                "1, 2, 3",
                dica="O range para antes do último número.",
            ),
            _lacuna(
                4,
                "Complete para mostrar cada fruta da lista.",
                "___ fruta ___ frutas:\n    print(fruta)",
                ["for", "in"],
                banco=["for", "in", "while", "if"],
            ),
            _escolha(
                5,
                "Quando o while para de repetir?",
                [
                    "Depois de 10 voltas",
                    "Quando a condição fica falsa",
                    "No fim do arquivo",
                    "Nunca",
                ],
                "Quando a condição fica falsa",
            ),
            _lacuna(
                6,
                "Complete para contar de 1 a 5 com while.",
                "n = 1\nwhile n ___ 5:\n    print(n)\n    n = n + 1",
                ["<="],
                banco=["<=", "<", ">="],
                dica="O 5 também precisa aparecer na tela.",
            ),
            _aberta(
                7,
                "Explique a diferença entre for e while com um exemplo do dia a dia.",
                "O for repete um número conhecido de vezes ou percorre uma lista; o while repete "
                "enquanto uma condição for verdadeira, sem saber de antemão quantas vezes.",
            ),
        ],
    },
    {
        "ordem": 9,
        "titulo": "Funções",
        "descricao": "Organize o código em blocos reutilizáveis.",
        "atividades": [
            _lacuna(
                1,
                "Complete a função que devolve o dobro do número.",
                "___ dobro(n):\n    ___ n * 2",
                ["def", "return"],
                banco=["def", "return", "print", "function"],
            ),
            _aberta(
                2,
                "Explique com suas palavras a diferença entre print e return.",
                "print mostra um valor na tela; return devolve o valor para quem "
                "chamou a função, que pode guardá-lo ou usá-lo em outra conta.",
            ),
            _escolha(
                3,
                "Com a função abaixo, quanto vale dobro(4)?",
                ["4", "8", "16", "n * 2"],
                "8",
                codigo="def dobro(n):\n    return n * 2",
            ),
            _escolha(
                4,
                "Como se chama o valor que a função recebe entre os parênteses?",
                ["Parâmetro", "Retorno", "Variável global", "Laço"],
                "Parâmetro",
            ),
            _ordenar(
                5,
                "Ordene para criar a função e depois usá-la.",
                ['print(saudacao("Ana"))', "def saudacao(nome):", '    return "Olá, " + nome'],
                ["def saudacao(nome):", '    return "Olá, " + nome', 'print(saudacao("Ana"))'],
                dica="A função precisa existir antes de ser chamada.",
            ),
            _lacuna(
                6,
                "Complete a função que soma dois números.",
                "def soma(a, b):\n    return a ___ b",
                ["+"],
                banco=["+", "-", "*"],
            ),
            _escolha(
                7,
                "O que uma função sem return devolve?",
                ["Dá erro", "None", "0", "O último valor calculado"],
                "None",
            ),
        ],
    },
    {
        "ordem": 10,
        "titulo": "Projeto: planejamento financeiro",
        "descricao": "Crie um programa capaz de salvar em lista seu gasto diário.",
        "atividades": [
            _escolha(
                1,
                "Qual estrutura guarda o gasto de cada dia?",
                ["Uma lista", "Um único número", "Um print", "Um if"],
                "Uma lista",
            ),
            _lacuna(
                2,
                "Complete para ler o gasto digitado e guardá-lo na lista.",
                'gasto = ___(input("Gasto de hoje: "))\ngastos.___(gasto)',
                ["float", "append"],
                banco=["float", "append", "print", "str"],
            ),
            _ordenar(
                3,
                "Ordene o programa que pede o gasto de três dias.",
                [
                    "    gastos.append(gasto)",
                    "gastos = []",
                    "for dia in range(3):",
                    '    gasto = float(input("Gasto: "))',
                ],
                [
                    "gastos = []",
                    "for dia in range(3):",
                    '    gasto = float(input("Gasto: "))',
                    "    gastos.append(gasto)",
                ],
            ),
            _lacuna(
                4,
                "Complete para somar todos os gastos.",
                "total = ___(gastos)",
                ["sum"],
                banco=["sum", "len", "max"],
            ),
            _escolha(
                5,
                "Qual linha avisa quando o total passa do orçamento?",
                [
                    "if total > orcamento:",
                    "if total = orcamento:",
                    "while total:",
                    "for total in orcamento:",
                ],
                "if total > orcamento:",
            ),
            _aberta(
                6,
                "Descreva, passo a passo, o que o seu programa de planejamento vai fazer.",
                "Criar uma lista vazia, pedir o gasto de cada dia, guardar cada um na lista, "
                "somar o total e avisar se ele passou do orçamento.",
            ),
            {
                "ordem": 7,
                "tipo": TipoAtividade.desafio_codigo,
                "enunciado": (
                    "Crie um programa de planejamento que salve em lista os gastos do dia. "
                    "Ele lê um gasto por linha, até uma linha vazia, e mostra o total com "
                    'duas casas decimais, assim: "Total: 12.50".'
                ),
                "dica": "Guarde cada valor numa lista com append e some no fim com sum().",
                "xp": 40,
                # Corrigido na sandbox (#34): o primeiro é o exemplo da tela, os
                # outros ficam ocultos.
                "casos": [
                    ("10\n2.5\n\n", "Total: 12.50", True),
                    ("\n", "Total: 0.00", False),
                    ("1.333\n1.333\n1.334\n\n", "Total: 4.00", False),
                ],
            },
        ],
    },
]


# Campos que uma atividade pode ter. A que não usa algum deles fica com ele
# vazio: sem isso, mudar uma atividade de tipo no seed deixaria, por exemplo,
# as alternativas da múltipla escolha que ela era antes.
CAMPOS_DA_ATIVIDADE = (
    "tipo",
    "enunciado",
    "dica",
    "opcoes",
    "codigo",
    "comando_esperado",
    "saida_esperada",
    "resposta_esperada",
    "tempo_sugerido_segundos",
    "xp",
)


def aplicar(db: Session) -> Trilha:
    trilha = db.execute(select(Trilha).where(Trilha.slug == SLUG)).scalar_one_or_none()
    if trilha is None:
        trilha = Trilha(slug=SLUG)
        db.add(trilha)

    trilha.nome = "Introdução Python"
    trilha.disciplina = "Introdução à Programação"
    trilha.categoria = "Linguagens"
    trilha.periodo = 1
    trilha.descricao = "Do primeiro comando no terminal ao seu primeiro programa."
    trilha.publicada = True
    db.flush()

    existentes = {modulo.ordem: modulo for modulo in trilha.modulos}

    for dados in MODULOS:
        modulo = existentes.get(dados["ordem"])
        if modulo is None:
            modulo = Modulo(trilha_id=trilha.id, ordem=dados["ordem"])
            db.add(modulo)

        modulo.titulo = dados["titulo"]
        modulo.descricao = dados.get("descricao")
        modulo.video_url = dados.get("video_url")
        db.flush()

        atividades_existentes = {atividade.ordem: atividade for atividade in modulo.atividades}
        for dados_atividade in dados["atividades"]:
            atividade = atividades_existentes.get(dados_atividade["ordem"])
            if atividade is None:
                atividade = Atividade(modulo_id=modulo.id, ordem=dados_atividade["ordem"])
                db.add(atividade)

            for campo in CAMPOS_DA_ATIVIDADE:
                setattr(atividade, campo, dados_atividade.get(campo))
            db.flush()
            _aplicar_casos(db, atividade, dados_atividade.get("casos", []))

    db.commit()
    return trilha


def _aplicar_casos(db: Session, atividade: Atividade, casos: list[tuple[str, str, bool]]) -> None:
    """Os casos de teste do desafio, na ordem. Rodar o seed de novo atualiza no lugar.

    Os que sobram saem: a atividade que deixou de ser desafio (a 1 do módulo 10
    já foi o desafio) não pode continuar com os casos dele.
    """
    existentes = {
        caso.ordem: caso
        for caso in db.scalars(select(CasoDeTeste).where(CasoDeTeste.atividade_id == atividade.id))
    }
    for ordem, (entrada, saida, publico) in enumerate(casos, start=1):
        caso = existentes.pop(ordem, None) or CasoDeTeste(atividade_id=atividade.id, ordem=ordem)
        caso.entrada, caso.saida_esperada, caso.publico = entrada, saida, publico
        db.add(caso)
    for sobra in existentes.values():
        db.delete(sobra)
