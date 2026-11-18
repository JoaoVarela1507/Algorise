"""Seed de mais cinco trilhas: Git, POO, Matemática Discreta, Ordenação e Redes.

Ampliam o catálogo com assuntos de graduação em computação do 2º ao 5º período,
usando o mesmo formato das trilhas extras: cada módulo tem 5 atividades (múltipla
escolha, lacuna, ordenação, outra múltipla escolha e resposta aberta) e o último
módulo fecha com o desafio de código, corrigido na sandbox pelos casos de teste.

Idempotente como os outros seeds: a trilha pelo slug, o módulo pela ordem, a
atividade pela ordem dentro do módulo.
"""

from sqlalchemy.orm import Session

from app.models import Trilha
from app.seeds.introducao_python import _aberta, _escolha, _lacuna, _ordenar
from app.seeds.trilhas_extras import _aplicar_trilha, _desafio

GIT: dict = {
    "slug": "git-e-controle-de-versao",
    "nome": "Git e Controle de Versão",
    "disciplina": "Engenharia de Software",
    "categoria": "Ferramentas",
    "periodo": 2,
    "descricao": "Versione seu código, trabalhe em equipe com branches e resolva conflitos.",
    "modulos": [
        {
            "ordem": 1,
            "titulo": "Por que versionar o código",
            "descricao": "O histórico do projeto guardado commit a commit, sem pastas 'final_v2'.",
            "atividades": [
                _escolha(
                    1,
                    "Qual é o principal objetivo de um sistema de controle de versão?",
                    [
                        "Deixar o programa mais rápido",
                        "Registrar o histórico de mudanças e permitir voltar a qualquer ponto",
                        "Compilar o código automaticamente",
                        "Impedir que mais de uma pessoa edite o projeto",
                    ],
                    "Registrar o histórico de mudanças e permitir voltar a qualquer ponto",
                ),
                _lacuna(
                    2,
                    "Complete o comando que cria um repositório Git na pasta atual.",
                    "git ___",
                    ["init"],
                    banco=["init", "start", "create"],
                ),
                _ordenar(
                    3,
                    "Ordene os passos para registrar uma alteração no histórico.",
                    [
                        "Gravar o commit com uma mensagem",
                        "Editar o arquivo",
                        "Adicionar o arquivo à área de preparação (git add)",
                    ],
                    [
                        "Editar o arquivo",
                        "Adicionar o arquivo à área de preparação (git add)",
                        "Gravar o commit com uma mensagem",
                    ],
                ),
                _escolha(
                    4,
                    "Git é um sistema de controle de versão distribuído. O que isso significa?",
                    [
                        "O código fica só num servidor central",
                        "Só funciona com internet",
                        "Cada pessoa tem uma cópia completa do repositório, com todo o histórico",
                        "Cada arquivo é guardado em um computador diferente",
                    ],
                    "Cada pessoa tem uma cópia completa do repositório, com todo o histórico",
                ),
                _aberta(
                    5,
                    "Cite dois problemas de versionar um projeto copiando a pasta com nomes "
                    "como 'projeto_final_v2'.",
                    "Fica difícil saber qual cópia é a mais nova, não dá para ver o que mudou "
                    "entre versões, o espaço é desperdiçado e duas pessoas editando cópias "
                    "diferentes não conseguem juntar o trabalho.",
                ),
            ],
        },
        {
            "ordem": 2,
            "titulo": "Commits, status e histórico",
            "descricao": "Os comandos do dia a dia: ver o que mudou, gravar e consultar o log.",
            "atividades": [
                _escolha(
                    1,
                    "Qual comando mostra quais arquivos foram modificados e quais estão "
                    "preparados para o commit?",
                    ["git log", "git status", "git commit", "git push"],
                    "git status",
                ),
                _lacuna(
                    2,
                    "Complete o commit com a mensagem 'corrige cálculo do total'.",
                    'git commit ___ "corrige cálculo do total"',
                    ["-m"],
                    banco=["-m", "-a", "-v"],
                ),
                _ordenar(
                    3,
                    "Ordene do comando que prepara ao que envia para o repositório remoto.",
                    ["git push", "git commit -m 'ajusta layout'", "git add ."],
                    ["git add .", "git commit -m 'ajusta layout'", "git push"],
                ),
                _escolha(
                    4,
                    "O que é uma boa mensagem de commit?",
                    [
                        "'alterações'",
                        "'ajusta o cálculo do frete para pedidos acima de R$ 100'",
                        "'asdf'",
                        "'commit 15'",
                    ],
                    "'ajusta o cálculo do frete para pedidos acima de R$ 100'",
                    dica="Quem lê o histórico precisa entender o que mudou e por quê.",
                ),
                _aberta(
                    5,
                    "Por que fazer commits pequenos e frequentes é melhor do que um commit "
                    "gigante no fim da semana?",
                    "Commits pequenos têm uma intenção clara, são fáceis de revisar, de "
                    "desfazer sozinhos e ajudam a achar em qual mudança um bug apareceu.",
                ),
            ],
        },
        {
            "ordem": 3,
            "titulo": "Branches e merge",
            "descricao": "Linhas paralelas de trabalho: crie, mude e junte.",
            "atividades": [
                _escolha(
                    1,
                    "O que é uma branch no Git?",
                    [
                        "Uma cópia do projeto em outro computador",
                        "Um tipo de erro de merge",
                        "Uma linha independente de desenvolvimento, com seus próprios commits",
                        "Um backup compactado do repositório",
                    ],
                    "Uma linha independente de desenvolvimento, com seus próprios commits",
                ),
                _lacuna(
                    2,
                    "Complete para criar a branch 'login' e já mudar para ela.",
                    "git ___ -b login",
                    ["checkout"],
                    banco=["checkout", "merge", "commit"],
                    dica="O comando git switch -c faz o mesmo nas versões novas.",
                ),
                _ordenar(
                    3,
                    "Ordene os passos para trazer a branch 'login' para a 'main'.",
                    [
                        "git merge login",
                        "git checkout main",
                        "Terminar os commits na branch login",
                    ],
                    [
                        "Terminar os commits na branch login",
                        "git checkout main",
                        "git merge login",
                    ],
                ),
                _escolha(
                    4,
                    "Quando acontece um conflito de merge?",
                    [
                        "Quando duas branches alteram as mesmas linhas de forma diferente",
                        "Sempre que duas branches existem",
                        "Quando o repositório tem muitos commits",
                        "Quando a mensagem de commit é longa",
                    ],
                    "Quando duas branches alteram as mesmas linhas de forma diferente",
                ),
                _aberta(
                    5,
                    "Explique por que desenvolver cada funcionalidade numa branch própria "
                    "ajuda o trabalho em equipe.",
                    "Cada pessoa trabalha isolada, sem quebrar a main nem atrapalhar os "
                    "colegas, e a funcionalidade só entra no projeto quando está pronta e "
                    "revisada.",
                ),
            ],
        },
        {
            "ordem": 4,
            "titulo": "Repositórios remotos e colaboração",
            "descricao": "Clone, push, pull e pull request: Git com o GitHub ou o GitLab.",
            "atividades": [
                _escolha(
                    1,
                    "Qual comando baixa uma cópia completa de um repositório remoto?",
                    ["git clone", "git init", "git fork", "git remote"],
                    "git clone",
                ),
                _lacuna(
                    2,
                    "Complete para enviar a branch 'login' ao remoto 'origin'.",
                    "git ___ origin login",
                    ["push"],
                    banco=["push", "pull", "fetch"],
                ),
                _ordenar(
                    3,
                    "Ordene o fluxo de uma contribuição com pull request.",
                    [
                        "Abrir o pull request",
                        "Criar uma branch e fazer os commits",
                        "Enviar a branch com git push",
                        "Receber a revisão e fazer o merge",
                    ],
                    [
                        "Criar uma branch e fazer os commits",
                        "Enviar a branch com git push",
                        "Abrir o pull request",
                        "Receber a revisão e fazer o merge",
                    ],
                ),
                _escolha(
                    4,
                    "Qual a diferença entre git fetch e git pull?",
                    [
                        "Não há diferença",
                        "O fetch só baixa as novidades; o pull baixa e já junta na branch atual",
                        "O pull só funciona no GitHub",
                        "O fetch apaga o histórico local",
                    ],
                    "O fetch só baixa as novidades; o pull baixa e já junta na branch atual",
                ),
                _aberta(
                    5,
                    "Para que serve o pull request, além de juntar o código?",
                    "Ele abre espaço para revisão: os colegas leem as mudanças, comentam, "
                    "pedem ajustes e rodam testes antes de o código entrar na branch principal.",
                ),
                _desafio(
                    6,
                    "Leia N e, em seguida, N linhas no formato do `git log` com autor: "
                    "hash, autor e mensagem, separados por espaço. Mostre quantos commits "
                    "cada autor fez, no formato `autor: total`, do que mais fez para o que "
                    "menos fez. Em caso de empate, siga a ordem alfabética do autor.",
                    "Separe cada linha com split(maxsplit=2), conte com um dicionário e "
                    "ordene por (-total, autor).",
                    [
                        (
                            "4\na1b2c3d ana corrige bug\n9f8e7d6 beto adiciona login\n"
                            "1c2d3e4 ana refatora\n5a6b7c8 ana ajusta teste\n",
                            "ana: 3\nbeto: 1",
                            True,
                        ),
                        (
                            "2\nabc1111 duda cria README\ndef2222 bia inicia projeto\n",
                            "bia: 1\nduda: 1",
                            False,
                        ),
                        (
                            "5\n1111111 eva inicial\n2222222 caio estilos\n3333333 eva rotas\n"
                            "4444444 caio testes\n5555555 fabi docs\n",
                            "caio: 2\neva: 2\nfabi: 1",
                            False,
                        ),
                    ],
                ),
            ],
        },
    ],
}

POO: dict = {
    "slug": "programacao-orientada-a-objetos",
    "nome": "Programação Orientada a Objetos",
    "disciplina": "Programação Orientada a Objetos",
    "categoria": "Linguagens",
    "periodo": 3,
    "descricao": "Classes, objetos, herança e polimorfismo, com exemplos em Python.",
    "modulos": [
        {
            "ordem": 1,
            "titulo": "Classes e objetos",
            "descricao": "A planta e a casa: como moldar dados e comportamentos juntos.",
            "atividades": [
                _escolha(
                    1,
                    "Qual a relação entre classe e objeto?",
                    [
                        "A classe é o molde; o objeto é uma instância criada a partir dele",
                        "O objeto é o molde; a classe é a cópia",
                        "São o mesmo conceito com nomes diferentes",
                        "A classe só existe depois de criar o objeto",
                    ],
                    "A classe é o molde; o objeto é uma instância criada a partir dele",
                ),
                _lacuna(
                    2,
                    "Complete a palavra que declara uma classe em Python.",
                    "___ Cachorro:\n    pass",
                    ["class"],
                    banco=["class", "def", "object"],
                ),
                _ordenar(
                    3,
                    "Ordene as linhas que criam a classe, instanciam e chamam um método.",
                    [
                        "rex.latir()",
                        "rex = Cachorro()",
                        "    def latir(self):\n        print('Au!')",
                        "class Cachorro:",
                    ],
                    [
                        "class Cachorro:",
                        "    def latir(self):\n        print('Au!')",
                        "rex = Cachorro()",
                        "rex.latir()",
                    ],
                ),
                _escolha(
                    4,
                    "O que é um atributo?",
                    [
                        "Uma função que o objeto executa",
                        "Uma variável que guarda um dado do objeto",
                        "Um tipo de erro da classe",
                        "O nome da classe",
                    ],
                    "Uma variável que guarda um dado do objeto",
                ),
                _aberta(
                    5,
                    "Dê um exemplo de classe do mundo real, com dois atributos e dois métodos.",
                    "Classe ContaBancaria: atributos titular e saldo; métodos depositar e sacar.",
                ),
            ],
        },
        {
            "ordem": 2,
            "titulo": "Construtor, self e encapsulamento",
            "descricao": "Inicialize o objeto e proteja o que não deve ser mexido de fora.",
            "atividades": [
                _escolha(
                    1,
                    "Qual método é chamado automaticamente ao criar um objeto em Python?",
                    ["__init__", "__main__", "__new_object__", "start"],
                    "__init__",
                ),
                _lacuna(
                    2,
                    "Complete o construtor que guarda o nome no objeto.",
                    "class Pessoa:\n    def __init__(___, nome):\n        self.nome = nome",
                    ["self"],
                    banco=["self", "this", "cls"],
                ),
                _ordenar(
                    3,
                    "Ordene as linhas da classe Conta.",
                    [
                        "        self.saldo = saldo",
                        "class Conta:",
                        "    def __init__(self, saldo):",
                    ],
                    [
                        "class Conta:",
                        "    def __init__(self, saldo):",
                        "        self.saldo = saldo",
                    ],
                ),
                _escolha(
                    4,
                    "O que é encapsulamento?",
                    [
                        "Esconder os detalhes internos e expor só uma interface controlada",
                        "Copiar uma classe para outra",
                        "Criar vários objetos de uma vez",
                        "Transformar uma classe em função",
                    ],
                    "Esconder os detalhes internos e expor só uma interface controlada",
                ),
                _aberta(
                    5,
                    "Por que um método sacar() que valida o saldo é melhor do que deixar "
                    "qualquer código alterar o atributo saldo direto?",
                    "O método garante a regra de negócio, como não deixar o saldo ficar "
                    "negativo; alterando o atributo direto, qualquer código poderia quebrar "
                    "essa regra.",
                ),
            ],
        },
        {
            "ordem": 3,
            "titulo": "Herança",
            "descricao": "Reaproveite uma classe criando outra que a estende.",
            "atividades": [
                _escolha(
                    1,
                    "O que a herança permite?",
                    [
                        "Apagar uma classe",
                        "Que uma classe filha reutilize atributos e métodos da classe mãe",
                        "Criar objetos sem classe",
                        "Executar o programa mais rápido",
                    ],
                    "Que uma classe filha reutilize atributos e métodos da classe mãe",
                ),
                _lacuna(
                    2,
                    "Complete para Gato herdar de Animal.",
                    "class Gato(___):\n    pass",
                    ["Animal"],
                    banco=["Animal", "Gato", "object()"],
                ),
                _ordenar(
                    3,
                    "Ordene a hierarquia, da mais geral para a mais específica.",
                    ["Poodle", "Animal", "Cachorro"],
                    ["Animal", "Cachorro", "Poodle"],
                ),
                _escolha(
                    4,
                    "Para que serve super() numa classe filha?",
                    [
                        "Chamar um método da classe mãe",
                        "Apagar o construtor da mãe",
                        "Criar uma nova classe",
                        "Tornar um atributo privado",
                    ],
                    "Chamar um método da classe mãe",
                ),
                _aberta(
                    5,
                    "Quando a herança é uma boa ideia? Dê um exemplo.",
                    "Quando a filha 'é um' tipo da mãe, como Cachorro é um Animal: ela "
                    "herda o comum e acrescenta ou ajusta o que é específico.",
                ),
            ],
        },
        {
            "ordem": 4,
            "titulo": "Polimorfismo e abstração",
            "descricao": "Mesma chamada, comportamentos diferentes conforme o objeto.",
            "atividades": [
                _escolha(
                    1,
                    "O que é polimorfismo?",
                    [
                        "Ter muitas classes no mesmo arquivo",
                        "Usar variáveis com vários tipos de dados",
                        "Objetos de classes diferentes responderem à mesma chamada, cada um "
                        "do seu jeito",
                        "Criar vários objetos iguais",
                    ],
                    "Objetos de classes diferentes responderem à mesma chamada, cada um "
                    "do seu jeito",
                ),
                _lacuna(
                    2,
                    "Complete a sobrescrita do método falar na classe Gato.",
                    "class Gato(Animal):\n    ___ falar(self):\n        print('Miau')",
                    ["def"],
                    banco=["def", "class", "return"],
                ),
                _ordenar(
                    3,
                    "Ordene o código que usa polimorfismo para mostrar o som dos animais.",
                    [
                        "for animal in animais:\n    animal.falar()",
                        "animais = [Cachorro(), Gato()]",
                        "class Gato(Animal): ...",
                        "class Cachorro(Animal): ...",
                    ],
                    [
                        "class Cachorro(Animal): ...",
                        "class Gato(Animal): ...",
                        "animais = [Cachorro(), Gato()]",
                        "for animal in animais:\n    animal.falar()",
                    ],
                ),
                _escolha(
                    4,
                    "O que é uma classe abstrata?",
                    [
                        "Uma classe sem atributos",
                        "Uma classe que não pode ser instanciada e serve de base para outras",
                        "Uma classe com nome curto",
                        "Uma classe criada em tempo de execução",
                    ],
                    "Uma classe que não pode ser instanciada e serve de base para outras",
                ),
                _aberta(
                    5,
                    "Como o polimorfismo reduz o uso de if/else em um programa?",
                    "Em vez de testar o tipo e escolher o comportamento com vários ifs, "
                    "chamamos o mesmo método e cada classe sabe o que fazer; novas classes "
                    "entram sem mudar o código que as usa.",
                ),
                _desafio(
                    6,
                    "Crie uma classe Conta com saldo inicial 0 e os métodos depositar e "
                    "sacar. O saque maior que o saldo não é feito e mostra `Saldo "
                    "insuficiente`. Leia N e, em seguida, N operações (`depositar valor` ou "
                    "`sacar valor`, com valores inteiros). No fim, mostre `Saldo: valor`.",
                    "O método sacar compara o valor com self.saldo antes de subtrair.",
                    [
                        (
                            "3\ndepositar 100\nsacar 30\nsacar 100\n",
                            "Saldo insuficiente\nSaldo: 70",
                            True,
                        ),
                        ("2\ndepositar 50\ndepositar 25\n", "Saldo: 75", False),
                        ("1\nsacar 10\n", "Saldo insuficiente\nSaldo: 0", False),
                    ],
                ),
            ],
        },
    ],
}

DISCRETA: dict = {
    "slug": "matematica-discreta",
    "nome": "Matemática Discreta para Computação",
    "disciplina": "Matemática Discreta",
    "categoria": "Matemática",
    "periodo": 2,
    "descricao": "Conjuntos, lógica, divisibilidade e contagem: a base matemática da computação.",
    "modulos": [
        {
            "ordem": 1,
            "titulo": "Conjuntos",
            "descricao": "Coleções sem repetição e as operações entre elas.",
            "atividades": [
                _escolha(
                    1,
                    "Dados A = {1, 2, 3} e B = {3, 4}, qual é a união de A e B?",
                    ["{3}", "{1, 2, 3, 4}", "{1, 2, 4}", "{1, 2, 3, 3, 4}"],
                    "{1, 2, 3, 4}",
                    dica="Na união entram todos os elementos, sem repetir.",
                ),
                _lacuna(
                    2,
                    "Complete para obter a interseção de dois conjuntos em Python.",
                    "a = {1, 2, 3}\nb = {3, 4}\nprint(a ___ b)",
                    ["&"],
                    banco=["&", "|", "-"],
                ),
                _ordenar(
                    3,
                    "Ordene os conjuntos do que tem menos ao que tem mais elementos.",
                    ["{1, 2, 3, 4}", "{}", "{7, 8}", "{5}"],
                    ["{}", "{5}", "{7, 8}", "{1, 2, 3, 4}"],
                ),
                _escolha(
                    4,
                    "Quantos elementos tem o conjunto das partes de {a, b, c}?",
                    ["3", "6", "8", "9"],
                    "8",
                    dica="Um conjunto com n elementos tem 2 elevado a n subconjuntos.",
                ),
                _aberta(
                    5,
                    "Qual a diferença entre uma lista e um conjunto em Python?",
                    "A lista guarda os elementos em ordem e aceita repetidos; o conjunto não "
                    "tem ordem nem repetidos e testa pertinência de forma muito rápida.",
                ),
            ],
        },
        {
            "ordem": 2,
            "titulo": "Lógica proposicional",
            "descricao": "Verdadeiro e falso, conectivos e tabelas-verdade.",
            "atividades": [
                _escolha(
                    1,
                    "Quando a conjunção (P e Q) é verdadeira?",
                    [
                        "Quando pelo menos uma é verdadeira",
                        "Quando as duas são verdadeiras",
                        "Quando as duas são falsas",
                        "Sempre",
                    ],
                    "Quando as duas são verdadeiras",
                ),
                _lacuna(
                    2,
                    "Complete a negação de uma proposição em Python.",
                    "chove = True\nprint(___ chove)",
                    ["not"],
                    banco=["not", "!", "~"],
                ),
                _ordenar(
                    3,
                    "Ordene os passos para avaliar not (P and Q) com P verdadeira e Q falsa.",
                    [
                        "not (P and Q) é Verdadeiro",
                        "P and Q é Falso",
                        "P é Verdadeiro e Q é Falso",
                    ],
                    [
                        "P é Verdadeiro e Q é Falso",
                        "P and Q é Falso",
                        "not (P and Q) é Verdadeiro",
                    ],
                ),
                _escolha(
                    4,
                    "A implicação P → Q só é falsa quando:",
                    [
                        "P é falsa e Q é verdadeira",
                        "P e Q são falsas",
                        "P é verdadeira e Q é falsa",
                        "P e Q são verdadeiras",
                    ],
                    "P é verdadeira e Q é falsa",
                ),
                _aberta(
                    5,
                    "Explique as leis de De Morgan com um exemplo.",
                    "A negação de (P e Q) é (não P) ou (não Q), e a negação de (P ou Q) é "
                    "(não P) e (não Q). Ex.: 'não (é maior e é par)' vale o mesmo que 'não é "
                    "maior ou não é par'.",
                ),
            ],
        },
        {
            "ordem": 3,
            "titulo": "Divisibilidade, MDC e primos",
            "descricao": "Restos, divisores e o algoritmo de Euclides.",
            "atividades": [
                _escolha(
                    1,
                    "Qual é o MDC de 12 e 18?",
                    ["2", "3", "6", "36"],
                    "6",
                ),
                _lacuna(
                    2,
                    "Complete o operador que dá o resto da divisão em Python.",
                    "print(17 ___ 5)  # mostra 2",
                    ["%"],
                    banco=["%", "//", "/"],
                ),
                _ordenar(
                    3,
                    "Ordene os passos do algoritmo de Euclides para o MDC de 48 e 18.",
                    [
                        "6 e 0: o MDC é 6",
                        "18 e 12 (resto de 48 por 18 é 12)",
                        "48 e 18",
                        "12 e 6 (resto de 18 por 12 é 6)",
                    ],
                    [
                        "48 e 18",
                        "18 e 12 (resto de 48 por 18 é 12)",
                        "12 e 6 (resto de 18 por 12 é 6)",
                        "6 e 0: o MDC é 6",
                    ],
                ),
                _escolha(
                    4,
                    "Qual destes números é primo?",
                    ["21", "27", "29", "33"],
                    "29",
                ),
                _aberta(
                    5,
                    "Explique como o MMC de dois números pode ser calculado a partir do MDC.",
                    "MMC(a, b) = a * b / MDC(a, b), porque o produto dos dois números "
                    "conta duas vezes os fatores comuns, que o MDC remove.",
                ),
            ],
        },
        {
            "ordem": 4,
            "titulo": "Contagem e combinatória",
            "descricao": "Princípio multiplicativo, permutações e combinações.",
            "atividades": [
                _escolha(
                    1,
                    "De quantas formas é possível formar uma fila com 4 pessoas?",
                    ["4", "16", "24", "12"],
                    "24",
                    dica="4! = 4 x 3 x 2 x 1.",
                ),
                _lacuna(
                    2,
                    "Complete a função do módulo math que calcula o fatorial.",
                    "import math\nprint(math.___(5))  # 120",
                    ["factorial"],
                    banco=["factorial", "fact", "prod"],
                ),
                _ordenar(
                    3,
                    "Ordene do menor para o maior valor.",
                    ["5! (120)", "3! (6)", "4! (24)", "0! (1)"],
                    ["0! (1)", "3! (6)", "4! (24)", "5! (120)"],
                ),
                _escolha(
                    4,
                    "Quantas combinações de 2 elementos existem num conjunto de 4 elementos?",
                    ["6", "8", "12", "4"],
                    "6",
                    dica="C(4, 2) = 4! / (2! x 2!).",
                ),
                _aberta(
                    5,
                    "Qual a diferença entre permutação e combinação?",
                    "Na permutação a ordem dos elementos importa (AB é diferente de BA); na "
                    "combinação não importa (AB e BA são o mesmo grupo).",
                ),
                _desafio(
                    6,
                    "Leia dois inteiros positivos numa linha, separados por espaço. Mostre "
                    "o MDC na primeira linha (`MDC: valor`) e o MMC na segunda (`MMC: valor`), "
                    "usando o algoritmo de Euclides.",
                    "Repita (a, b) = (b, a % b) até b chegar a 0; o MMC é a * b // MDC.",
                    [
                        ("12 18\n", "MDC: 6\nMMC: 36", True),
                        ("7 13\n", "MDC: 1\nMMC: 91", False),
                        ("100 75\n", "MDC: 25\nMMC: 300", False),
                    ],
                ),
            ],
        },
    ],
}

REDES: dict = {
    "slug": "redes-de-computadores",
    "nome": "Redes de Computadores",
    "disciplina": "Redes de Computadores",
    "categoria": "Infraestrutura",
    "periodo": 5,
    "descricao": "Camadas, endereços IP, TCP e DNS: como os dados viajam pela rede.",
    "modulos": [
        {
            "ordem": 1,
            "titulo": "Modelo em camadas",
            "descricao": "OSI e TCP/IP: dividir o problema para a rede ficar simples.",
            "atividades": [
                _escolha(
                    1,
                    "Por que as redes são organizadas em camadas?",
                    [
                        "Para cada camada resolver uma parte do problema e poder mudar sem "
                        "afetar as outras",
                        "Para a rede ficar mais lenta e segura",
                        "Porque os cabos têm camadas",
                        "Para usar apenas um protocolo",
                    ],
                    "Para cada camada resolver uma parte do problema e poder mudar sem "
                    "afetar as outras",
                ),
                _lacuna(
                    2,
                    "Complete: o modelo de referência com 7 camadas se chama ___.",
                    "Modelo ___ (7 camadas)",
                    ["OSI"],
                    banco=["OSI", "TCP", "HTTP"],
                ),
                _ordenar(
                    3,
                    "Ordene as camadas do modelo TCP/IP, da mais alta (aplicação) à mais "
                    "baixa (enlace).",
                    ["Enlace", "Aplicação", "Internet (rede)", "Transporte"],
                    ["Aplicação", "Transporte", "Internet (rede)", "Enlace"],
                ),
                _escolha(
                    4,
                    "Em qual camada do modelo TCP/IP atuam o HTTP e o DNS?",
                    ["Aplicação", "Transporte", "Internet", "Enlace"],
                    "Aplicação",
                ),
                _aberta(
                    5,
                    "Explique, com suas palavras, o que é encapsulamento de dados nas camadas.",
                    "Ao descer pelas camadas, cada uma acrescenta seu cabeçalho aos dados "
                    "recebidos de cima; no destino, cada camada retira o seu cabeçalho e "
                    "entrega o restante para a de cima.",
                ),
            ],
        },
        {
            "ordem": 2,
            "titulo": "Endereçamento IP",
            "descricao": "IPv4, máscaras de sub-rede e as classes de endereço.",
            "atividades": [
                _escolha(
                    1,
                    "Quantos bits tem um endereço IPv4?",
                    ["16", "32", "64", "128"],
                    "32",
                ),
                _lacuna(
                    2,
                    "Complete: um endereço IPv4 é escrito em ___ números de 0 a 255 "
                    "separados por pontos.",
                    "IPv4 = ___ octetos",
                    ["4"],
                    banco=["4", "6", "8"],
                ),
                _ordenar(
                    3,
                    "Ordene as classes de endereço pelo primeiro octeto, da menor faixa à maior.",
                    [
                        "Classe C (192 a 223)",
                        "Classe A (0 a 127)",
                        "Classe B (128 a 191)",
                    ],
                    [
                        "Classe A (0 a 127)",
                        "Classe B (128 a 191)",
                        "Classe C (192 a 223)",
                    ],
                ),
                _escolha(
                    4,
                    "O que representa a máscara 255.255.255.0 (/24)?",
                    [
                        "Os 24 primeiros bits identificam a rede e os 8 últimos, o host",
                        "Os 8 primeiros bits identificam a rede",
                        "O endereço é inválido",
                        "A rede tem 24 hosts",
                    ],
                    "Os 24 primeiros bits identificam a rede e os 8 últimos, o host",
                ),
                _aberta(
                    5,
                    "Qual a diferença entre um endereço IP público e um privado "
                    "(como 192.168.0.10)?",
                    "O público é roteável na internet e único no mundo; o privado só vale "
                    "dentro de redes locais e pode se repetir em redes diferentes, saindo "
                    "para a internet por NAT.",
                ),
            ],
        },
        {
            "ordem": 3,
            "titulo": "TCP, UDP e portas",
            "descricao": "Transporte confiável ou rápido: quando usar cada um.",
            "atividades": [
                _escolha(
                    1,
                    "Qual protocolo de transporte garante entrega ordenada e confiável?",
                    ["UDP", "TCP", "IP", "ARP"],
                    "TCP",
                ),
                _lacuna(
                    2,
                    "Complete: a porta padrão do HTTPS é a ___.",
                    "https://exemplo.com  ->  porta ___",
                    ["443"],
                    banco=["443", "80", "22"],
                ),
                _ordenar(
                    3,
                    "Ordene as etapas do handshake de três vias do TCP.",
                    ["ACK", "SYN", "SYN-ACK"],
                    ["SYN", "SYN-ACK", "ACK"],
                ),
                _escolha(
                    4,
                    "Qual aplicação costuma preferir UDP?",
                    [
                        "Transferência de arquivos",
                        "Chamada de vídeo ao vivo",
                        "Envio de e-mail",
                        "Acesso a um banco de dados",
                    ],
                    "Chamada de vídeo ao vivo",
                    dica="Melhor perder um quadro do que atrasar toda a conversa.",
                ),
                _aberta(
                    5,
                    "Para que servem as portas, se o IP já identifica o computador?",
                    "O IP identifica a máquina; a porta identifica qual aplicação nela deve "
                    "receber os dados, permitindo vários serviços ao mesmo tempo.",
                ),
            ],
        },
        {
            "ordem": 4,
            "titulo": "DNS e HTTP",
            "descricao": "Do nome do site à página na tela.",
            "atividades": [
                _escolha(
                    1,
                    "Qual a função do DNS?",
                    [
                        "Criptografar as conexões",
                        "Traduzir nomes de domínio em endereços IP",
                        "Entregar e-mails",
                        "Distribuir endereços IP aos computadores",
                    ],
                    "Traduzir nomes de domínio em endereços IP",
                ),
                _lacuna(
                    2,
                    "Complete o método HTTP usado para buscar uma página.",
                    "___ /index.html HTTP/1.1\nHost: exemplo.com",
                    ["GET"],
                    banco=["GET", "POST", "PUT"],
                ),
                _ordenar(
                    3,
                    "Ordene o que acontece ao abrir um site no navegador.",
                    [
                        "O servidor devolve a página",
                        "O navegador pede o endereço IP ao DNS",
                        "O navegador envia a requisição HTTP",
                        "O usuário digita o endereço do site",
                    ],
                    [
                        "O usuário digita o endereço do site",
                        "O navegador pede o endereço IP ao DNS",
                        "O navegador envia a requisição HTTP",
                        "O servidor devolve a página",
                    ],
                ),
                _escolha(
                    4,
                    "O que significa o código de status HTTP 404?",
                    [
                        "Erro interno do servidor",
                        "Recurso não encontrado",
                        "Requisição com sucesso",
                        "Acesso redirecionado",
                    ],
                    "Recurso não encontrado",
                ),
                _aberta(
                    5,
                    "Qual a vantagem de HTTPS sobre HTTP?",
                    "O HTTPS criptografa a conexão e autentica o servidor, então ninguém no "
                    "caminho consegue ler ou alterar os dados, como senhas e cartões.",
                ),
                _desafio(
                    6,
                    "Leia um endereço IPv4. Se não tiver 4 números inteiros entre 0 e 255 "
                    "separados por ponto, mostre `Invalido`. Caso contrário, mostre a classe "
                    "pelo primeiro octeto: `Classe A` (0 a 127), `Classe B` (128 a 191), "
                    "`Classe C` (192 a 223), `Classe D` (224 a 239) ou `Classe E` (240 a 255).",
                    "Use split('.'), confira com isdigit() e int() e depois compare o "
                    "primeiro octeto com as faixas.",
                    [
                        ("192.168.0.10\n", "Classe C", True),
                        ("256.10.0.1\n", "Invalido", False),
                        ("172.16.0.5\n", "Classe B", False),
                    ],
                ),
            ],
        },
    ],
}

ORDENACAO: dict = {
    "slug": "ordenacao-e-complexidade",
    "nome": "Algoritmos de Ordenação e Complexidade",
    "disciplina": "Análise de Algoritmos",
    "categoria": "Fundamentos",
    "periodo": 4,
    "descricao": "Big-O e os algoritmos clássicos de ordenação: como comparar e escolher.",
    "modulos": [
        {
            "ordem": 1,
            "titulo": "Complexidade e notação Big-O",
            "descricao": "Medir o custo de um algoritmo pelo crescimento, não pelo cronômetro.",
            "atividades": [
                _escolha(
                    1,
                    "O que a notação Big-O descreve?",
                    [
                        "O tempo exato em segundos",
                        "Como o custo do algoritmo cresce conforme a entrada aumenta",
                        "O número de linhas do código",
                        "A linguagem usada",
                    ],
                    "Como o custo do algoritmo cresce conforme a entrada aumenta",
                ),
                _lacuna(
                    2,
                    "Complete: percorrer uma lista de n itens uma vez tem custo O(___).",
                    "for x in lista:\n    print(x)  # custo O(___)",
                    ["n"],
                    banco=["n", "1", "n²"],
                ),
                _ordenar(
                    3,
                    "Ordene as complexidades da que cresce mais devagar à que cresce mais rápido.",
                    ["O(n²)", "O(1)", "O(n log n)", "O(n)"],
                    ["O(1)", "O(n)", "O(n log n)", "O(n²)"],
                ),
                _escolha(
                    4,
                    "Dois laços for aninhados, cada um com n voltas, têm custo:",
                    ["O(n)", "O(2n)", "O(n²)", "O(log n)"],
                    "O(n²)",
                ),
                _aberta(
                    5,
                    "Por que ignoramos constantes e termos menores no Big-O, como em "
                    "3n² + 5n + 2 virando O(n²)?",
                    "Para entradas grandes, o termo de maior crescimento domina o custo; "
                    "constantes e termos menores mudam pouco a forma como o custo cresce.",
                ),
            ],
        },
        {
            "ordem": 2,
            "titulo": "Bubble Sort e Selection Sort",
            "descricao": "Os dois algoritmos mais simples, com custo quadrático.",
            "atividades": [
                _escolha(
                    1,
                    "Como o Bubble Sort ordena a lista?",
                    [
                        "Divide a lista ao meio várias vezes",
                        "Compara pares vizinhos e troca os que estão fora de ordem, repetidamente",
                        "Escolhe um pivô e particiona a lista",
                        "Sorteia a ordem até acertar",
                    ],
                    "Compara pares vizinhos e troca os que estão fora de ordem, repetidamente",
                ),
                _lacuna(
                    2,
                    "Complete a troca de dois elementos no Bubble Sort.",
                    "if v[j] > v[j + 1]:\n    v[j], v[j + 1] = v[j + 1], ___",
                    ["v[j]"],
                    banco=["v[j]", "v[j + 1]", "j"],
                ),
                _ordenar(
                    3,
                    "Ordene os passos do Selection Sort.",
                    [
                        "Repetir para o restante da lista",
                        "Colocar o menor na primeira posição",
                        "Achar o menor elemento da parte não ordenada",
                    ],
                    [
                        "Achar o menor elemento da parte não ordenada",
                        "Colocar o menor na primeira posição",
                        "Repetir para o restante da lista",
                    ],
                ),
                _escolha(
                    4,
                    "Qual a complexidade de tempo do Bubble Sort no pior caso?",
                    ["O(n)", "O(n²)", "O(n log n)", "O(log n)"],
                    "O(n²)",
                ),
                _aberta(
                    5,
                    "Por que o Bubble Sort é pouco usado na prática, mesmo sendo fácil de "
                    "entender?",
                    "O custo quadrático faz o tempo explodir em listas grandes; existem "
                    "algoritmos como Merge Sort e Quicksort muito mais rápidos.",
                ),
            ],
        },
        {
            "ordem": 3,
            "titulo": "Insertion Sort e Merge Sort",
            "descricao": "Inserir no lugar certo e dividir para conquistar.",
            "atividades": [
                _escolha(
                    1,
                    "Qual a ideia do Insertion Sort?",
                    [
                        "Inserir cada elemento na posição certa da parte já ordenada",
                        "Dividir a lista em duas e juntar",
                        "Sempre trocar o primeiro com o último",
                        "Contar quantas vezes cada valor aparece",
                    ],
                    "Inserir cada elemento na posição certa da parte já ordenada",
                ),
                _lacuna(
                    2,
                    "Complete: o Merge Sort divide a lista ao ___ e ordena cada metade.",
                    "O Merge Sort divide a lista ao ___.",
                    ["meio"],
                    banco=["meio", "fim", "acaso"],
                ),
                _ordenar(
                    3,
                    "Ordene os passos do Merge Sort.",
                    [
                        "Juntar as duas metades ordenadas",
                        "Ordenar cada metade (recursivamente)",
                        "Dividir a lista ao meio",
                    ],
                    [
                        "Dividir a lista ao meio",
                        "Ordenar cada metade (recursivamente)",
                        "Juntar as duas metades ordenadas",
                    ],
                ),
                _escolha(
                    4,
                    "Qual a complexidade de tempo do Merge Sort?",
                    ["O(n²)", "O(n)", "O(log n)", "O(n log n)"],
                    "O(n log n)",
                ),
                _aberta(
                    5,
                    "Que vantagem e que desvantagem o Merge Sort tem em relação ao Insertion Sort?",
                    "É muito mais rápido em listas grandes, O(n log n) contra O(n²), mas "
                    "usa memória extra para as listas auxiliares e é mais complexo de "
                    "implementar.",
                ),
            ],
        },
        {
            "ordem": 4,
            "titulo": "Comparando algoritmos na prática",
            "descricao": "Estabilidade, Quicksort, sort do Python e como escolher.",
            "atividades": [
                _escolha(
                    1,
                    "O que é um algoritmo de ordenação estável?",
                    [
                        "Nunca trava",
                        "Mantém a ordem original de elementos com chaves iguais",
                        "Só funciona em listas pequenas",
                        "Usa memória constante",
                    ],
                    "Mantém a ordem original de elementos com chaves iguais",
                ),
                _lacuna(
                    2,
                    "Complete para devolver uma nova lista ordenada em Python.",
                    "numeros = [3, 1, 2]\nprint(___(numeros))",
                    ["sorted"],
                    banco=["sorted", "sort", "order"],
                ),
                _ordenar(
                    3,
                    "Ordene do mais lento ao mais rápido, para listas grandes.",
                    [
                        "Merge Sort: O(n log n)",
                        "Varrer a lista uma vez: O(n)",
                        "Bubble Sort: O(n²)",
                    ],
                    [
                        "Bubble Sort: O(n²)",
                        "Merge Sort: O(n log n)",
                        "Varrer a lista uma vez: O(n)",
                    ],
                    dica="Compare as ordens de crescimento: n² > n log n > n.",
                ),
                _escolha(
                    4,
                    "Qual o pior caso do Quicksort e quando ele acontece?",
                    [
                        "O(n²), quando o pivô escolhido divide muito mal a lista",
                        "O(n), quando a lista já está ordenada",
                        "O(log n), com listas pequenas",
                        "Nunca tem pior caso",
                    ],
                    "O(n²), quando o pivô escolhido divide muito mal a lista",
                ),
                _aberta(
                    5,
                    "Na prática, por que usar o sorted() do Python em vez de escrever o "
                    "próprio algoritmo de ordenação?",
                    "O sorted() usa o Timsort, estável, muito testado e otimizado, com "
                    "O(n log n) no pior caso; escrever o próprio traz bugs e normalmente fica "
                    "mais lento.",
                ),
                _desafio(
                    6,
                    "Implemente o Bubble Sort contando as trocas. Leia uma linha com números "
                    "inteiros separados por espaço e mostre a lista ordenada na primeira "
                    "linha (separada por espaço) e `Trocas: n` na segunda, com n sendo o "
                    "total de trocas feitas pelo algoritmo.",
                    "Troque v[j] e v[j + 1] quando v[j] > v[j + 1] e some 1 a cada troca.",
                    [
                        ("5 2 4 1\n", "1 2 4 5\nTrocas: 5", True),
                        ("1 2 3\n", "1 2 3\nTrocas: 0", False),
                        ("3 2 1\n", "1 2 3\nTrocas: 3", False),
                    ],
                ),
            ],
        },
    ],
}

TRILHAS = (GIT, POO, DISCRETA, REDES, ORDENACAO)


def aplicar(db: Session) -> list[Trilha]:
    """Grava as cinco trilhas e devolve-as, na ordem de `TRILHAS`."""
    return [_aplicar_trilha(db, dados) for dados in TRILHAS]
