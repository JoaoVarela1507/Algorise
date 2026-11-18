"""Seed de mais três trilhas: Lógica de Programação, Estruturas de Dados e SQL.

Completam o catálogo além da "Introdução Python", com uma trilha por período
(1º, 2º e 3º) e categorias diferentes, para a tela de trilhas, os filtros e o
ranking terem com o que trabalhar.

Idempotente como o seed da Introdução Python (e com as mesmas funções de
atividade): a trilha pelo slug, o módulo pela ordem, a atividade pela ordem
dentro do módulo.

Cada módulo tem 5 atividades e fecha o assunto: múltipla escolha, lacuna,
ordenação, outra múltipla escolha e uma resposta aberta. O último módulo de cada
trilha traz também o desafio proposto (#25), que fecha a trilha e é corrigido na
sandbox pelos casos de teste.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Atividade, Modulo, TipoAtividade, Trilha
from app.seeds.introducao_python import (
    CAMPOS_DA_ATIVIDADE,
    _aberta,
    _aplicar_casos,
    _escolha,
    _lacuna,
    _ordenar,
)


def _desafio(ordem: int, enunciado: str, dica: str, casos: list[tuple[str, str, bool]]) -> dict:
    """O desafio proposto da trilha: o primeiro caso é o exemplo da tela, os outros ocultos."""
    return {
        "ordem": ordem,
        "tipo": TipoAtividade.desafio_codigo,
        "enunciado": enunciado,
        "dica": dica,
        "xp": 40,
        "casos": casos,
    }


LOGICA: dict = {
    "slug": "logica-de-programacao",
    "nome": "Lógica de Programação",
    "disciplina": "Introdução à Programação",
    "categoria": "Fundamentos",
    "periodo": 1,
    "descricao": "Pense como um programador: algoritmos, variáveis, decisões e repetições.",
    "modulos": [
        {
            "ordem": 1,
            "titulo": "Algoritmos e sequência",
            "descricao": "Um algoritmo é uma receita: passos claros, numa ordem que importa.",
            "atividades": [
                _escolha(
                    1,
                    "O que é um algoritmo?",
                    [
                        "Uma sequência finita de passos para resolver um problema",
                        "Um tipo de computador",
                        "Uma linguagem de programação",
                        "Um erro no programa",
                    ],
                    "Uma sequência finita de passos para resolver um problema",
                ),
                _lacuna(
                    2,
                    "Complete: um algoritmo precisa ter um ___ e um fim bem definidos.",
                    "Todo algoritmo tem um ___ e um fim.",
                    ["início"],
                    banco=["início", "erro", "loop"],
                ),
                _ordenar(
                    3,
                    "Ordene os passos do algoritmo de fazer café.",
                    [
                        "Servir o café",
                        "Ferver a água",
                        "Colocar o pó no filtro",
                        "Despejar a água no filtro",
                    ],
                    [
                        "Ferver a água",
                        "Colocar o pó no filtro",
                        "Despejar a água no filtro",
                        "Servir o café",
                    ],
                ),
                _escolha(
                    4,
                    "Por que a ordem dos passos importa num algoritmo?",
                    [
                        "Porque cada passo pode depender do resultado do anterior",
                        "Porque o computador lê de trás para frente",
                        "Não importa, o resultado é sempre o mesmo",
                        "Porque passos fora de ordem rodam mais rápido",
                    ],
                    "Porque cada passo pode depender do resultado do anterior",
                ),
                _aberta(
                    5,
                    "Escreva um algoritmo, em passos numerados, para trocar uma lâmpada.",
                    "1. Desligar o interruptor. 2. Pegar uma escada. 3. Retirar a lâmpada "
                    "queimada. 4. Colocar a lâmpada nova. 5. Ligar o interruptor para testar.",
                ),
            ],
        },
        {
            "ordem": 2,
            "titulo": "Variáveis e tipos de dados",
            "descricao": "Guarde valores com nome e entenda a diferença entre número e texto.",
            "atividades": [
                _escolha(
                    1,
                    "O que é uma variável?",
                    [
                        "Um espaço com nome que guarda um valor",
                        "Um comando que repete código",
                        "Um tipo de erro",
                        "Um arquivo do sistema",
                    ],
                    "Um espaço com nome que guarda um valor",
                ),
                _lacuna(
                    2,
                    "Complete para guardar a idade 18 na variável idade.",
                    "idade ___ 18",
                    ["="],
                    banco=["=", "==", ":"],
                ),
                _ordenar(
                    3,
                    "Ordene do tipo mais simples ao que guarda vários valores.",
                    ["Lista", "Booleano", "Texto (string)"],
                    ["Booleano", "Texto (string)", "Lista"],
                    dica="O booleano só tem dois valores possíveis.",
                ),
                _escolha(
                    4,
                    'Qual é o tipo do valor "42" (com aspas)?',
                    ["Texto (string)", "Número inteiro", "Número decimal", "Booleano"],
                    "Texto (string)",
                    dica="As aspas fazem toda a diferença.",
                ),
                _aberta(
                    5,
                    'Explique a diferença entre os valores 7 e "7".',
                    '7 é um número, com o qual se pode fazer contas. "7" é um texto: as aspas '
                    "dizem que é uma sequência de caracteres, e somar dois textos os junta.",
                ),
            ],
        },
        {
            "ordem": 3,
            "titulo": "Decisões com se e senão",
            "descricao": "Faça o programa escolher um caminho conforme uma condição.",
            "atividades": [
                _escolha(
                    1,
                    "Qual é o resultado de 5 > 3 e 2 > 4?",
                    ["Falso", "Verdadeiro", "Erro", "5"],
                    "Falso",
                    dica="No 'e', as duas condições precisam ser verdadeiras.",
                ),
                _lacuna(
                    2,
                    "Complete a decisão que confere a maioridade.",
                    'se idade ___ 18 então\n    escreva("Maior de idade")',
                    [">="],
                    banco=[">=", "<", "="],
                ),
                _ordenar(
                    3,
                    "Ordene as linhas da decisão que aprova quem tirou 7 ou mais.",
                    [
                        '    escreva("Reprovado")',
                        "se nota >= 7 então",
                        "senão",
                        '    escreva("Aprovado")',
                    ],
                    [
                        "se nota >= 7 então",
                        '    escreva("Aprovado")',
                        "senão",
                        '    escreva("Reprovado")',
                    ],
                ),
                _escolha(
                    4,
                    "Quando o bloco senão é executado?",
                    [
                        "Quando a condição do se é falsa",
                        "Sempre, depois do se",
                        "Quando a condição do se é verdadeira",
                        "Nunca",
                    ],
                    "Quando a condição do se é falsa",
                ),
                _aberta(
                    5,
                    "Dê um exemplo do dia a dia em que você toma uma decisão com se e senão.",
                    "Se estiver chovendo, levo o guarda-chuva; senão, saio sem ele.",
                ),
            ],
        },
        {
            "ordem": 4,
            "titulo": "Repetições com enquanto e para",
            "descricao": "Repita passos sem copiar código: contadores e condições de parada.",
            "atividades": [
                _escolha(
                    1,
                    "Quantas vezes o laço 'para i de 1 até 5' executa?",
                    ["5", "4", "6", "Infinitas"],
                    "5",
                ),
                _lacuna(
                    2,
                    "Complete para o laço parar quando o contador chegar a 10.",
                    "contador = 0\nenquanto contador ___ 10 faça\n    contador = contador + 1",
                    ["<"],
                    banco=["<", ">", "=="],
                ),
                _ordenar(
                    3,
                    "Ordene o algoritmo que soma os números de 1 a 3.",
                    [
                        "escreva(soma)",
                        "soma = 0",
                        "para i de 1 até 3 faça",
                        "    soma = soma + i",
                    ],
                    [
                        "soma = 0",
                        "para i de 1 até 3 faça",
                        "    soma = soma + i",
                        "escreva(soma)",
                    ],
                ),
                _escolha(
                    4,
                    "O que causa um laço infinito?",
                    [
                        "Uma condição de parada que nunca fica falsa",
                        "Um laço com poucas linhas",
                        "Usar o comando para",
                        "Uma variável com nome longo",
                    ],
                    "Uma condição de parada que nunca fica falsa",
                ),
                _aberta(
                    5,
                    "Quando usar enquanto em vez de para?",
                    "O para serve quando se sabe quantas vezes repetir; o enquanto, quando a "
                    "repetição depende de uma condição que muda durante a execução.",
                ),
                _desafio(
                    6,
                    "Faça uma contagem regressiva: leia um número N e mostre de N até 1, "
                    'um por linha, e no fim "Fim!".',
                    "Use um laço que começa em N e diminui 1 a cada volta.",
                    [
                        ("3\n", "3\n2\n1\nFim!", True),
                        ("1\n", "1\nFim!", False),
                        ("0\n", "Fim!", False),
                    ],
                ),
            ],
        },
    ],
}

ESTRUTURAS: dict = {
    "slug": "estruturas-de-dados",
    "nome": "Estruturas de Dados",
    "disciplina": "Algoritmos e Estruturas de Dados",
    "categoria": "Fundamentos",
    "periodo": 2,
    "descricao": "Listas, pilhas, filas e busca: como organizar dados para o programa render.",
    "modulos": [
        {
            "ordem": 1,
            "titulo": "Listas",
            "descricao": "Vários valores numa variável só, acessados pela posição.",
            "atividades": [
                _escolha(
                    1,
                    "Em Python, qual é o índice do primeiro elemento de uma lista?",
                    ["0", "1", "-1", "Depende da lista"],
                    "0",
                ),
                _lacuna(
                    2,
                    "Complete para acrescentar 4 no fim da lista.",
                    "numeros = [1, 2, 3]\nnumeros.___(4)",
                    ["append"],
                    banco=["append", "remove", "insert"],
                ),
                _ordenar(
                    3,
                    "Ordene as linhas que criam uma lista, acrescentam um item e mostram o total.",
                    ["print(len(frutas))", 'frutas = ["maçã"]', 'frutas.append("uva")'],
                    ['frutas = ["maçã"]', 'frutas.append("uva")', "print(len(frutas))"],
                ),
                _escolha(
                    4,
                    "O que len([10, 20, 30]) devolve?",
                    ["3", "30", "60", "2"],
                    "3",
                ),
                _aberta(
                    5,
                    "Por que guardar as notas de uma turma numa lista, e não em 40 variáveis?",
                    "Com a lista dá para percorrer todas as notas num laço, somar, contar e "
                    "ordenar sem repetir código, e a turma pode ter qualquer tamanho.",
                ),
            ],
        },
        {
            "ordem": 2,
            "titulo": "Pilhas",
            "descricao": "O último a entrar é o primeiro a sair: desfazer, voltar, recursão.",
            "atividades": [
                _escolha(
                    1,
                    "Qual regra define uma pilha?",
                    [
                        "LIFO: o último a entrar é o primeiro a sair",
                        "FIFO: o primeiro a entrar é o primeiro a sair",
                        "Os itens saem em ordem alfabética",
                        "Os itens saem em ordem aleatória",
                    ],
                    "LIFO: o último a entrar é o primeiro a sair",
                ),
                _lacuna(
                    2,
                    "Complete para tirar o item do topo da pilha.",
                    "pilha = [1, 2, 3]\ntopo = pilha.___()",
                    ["pop"],
                    banco=["pop", "append", "sort"],
                ),
                _ordenar(
                    3,
                    "Empilhe A, depois B, depois C. Em que ordem eles saem?",
                    ["A", "C", "B"],
                    ["C", "B", "A"],
                ),
                _escolha(
                    4,
                    "Qual destes usa uma pilha?",
                    [
                        "O botão desfazer (Ctrl+Z) de um editor",
                        "A fila do banco",
                        "A ordem alfabética de uma agenda",
                        "Uma playlist em modo aleatório",
                    ],
                    "O botão desfazer (Ctrl+Z) de um editor",
                ),
                _aberta(
                    5,
                    "Explique como o botão voltar do navegador funciona como uma pilha.",
                    "Cada página visitada é empilhada. Voltar desempilha a do topo, que é a "
                    "última visitada, e mostra a de baixo.",
                ),
            ],
        },
        {
            "ordem": 3,
            "titulo": "Filas",
            "descricao": "O primeiro a chegar é o primeiro a ser atendido.",
            "atividades": [
                _escolha(
                    1,
                    "Qual regra define uma fila?",
                    [
                        "FIFO: o primeiro a entrar é o primeiro a sair",
                        "LIFO: o último a entrar é o primeiro a sair",
                        "O maior item sai primeiro",
                        "Qualquer item pode sair a qualquer hora",
                    ],
                    "FIFO: o primeiro a entrar é o primeiro a sair",
                ),
                _lacuna(
                    2,
                    "Complete com a estrutura do Python feita para filas.",
                    "from collections import ___\nfila = ___()",
                    ["deque", "deque"],
                    banco=["deque", "list", "dict"],
                ),
                _ordenar(
                    3,
                    "Ana, Beto e Caio entram na fila nessa ordem. Em que ordem são atendidos?",
                    ["Caio", "Ana", "Beto"],
                    ["Ana", "Beto", "Caio"],
                ),
                _escolha(
                    4,
                    "Qual destes é um exemplo de fila?",
                    [
                        "A fila de impressão de documentos",
                        "O histórico do botão voltar",
                        "Uma pilha de pratos",
                        "O desfazer de um editor",
                    ],
                    "A fila de impressão de documentos",
                ),
                _aberta(
                    5,
                    "Qual a diferença entre pilha e fila? Dê um exemplo de cada.",
                    "Na pilha sai primeiro o último que entrou (desfazer de um editor); na fila "
                    "sai primeiro o que entrou antes (atendimento de banco).",
                ),
            ],
        },
        {
            "ordem": 4,
            "titulo": "Busca linear e binária",
            "descricao": "Achar um valor olhando um por um, ou cortando a lista ao meio.",
            "atividades": [
                _escolha(
                    1,
                    "O que a busca binária exige da lista?",
                    [
                        "Que esteja ordenada",
                        "Que tenha tamanho par",
                        "Que só tenha números positivos",
                        "Nada, funciona com qualquer lista",
                    ],
                    "Que esteja ordenada",
                ),
                _lacuna(
                    2,
                    "Complete a busca linear: devolve a posição do alvo ou -1.",
                    "for i in range(len(lista)):\n"
                    "    if lista[i] ___ alvo:\n"
                    "        return i\n"
                    "return -1",
                    ["=="],
                    banco=["==", "=", "!="],
                ),
                _ordenar(
                    3,
                    "Ordene os passos da busca binária.",
                    [
                        "Se o alvo for menor, continuar na metade da esquerda",
                        "Olhar o elemento do meio",
                        "Repetir até achar ou a faixa ficar vazia",
                        "Se for igual ao alvo, terminar",
                    ],
                    [
                        "Olhar o elemento do meio",
                        "Se for igual ao alvo, terminar",
                        "Se o alvo for menor, continuar na metade da esquerda",
                        "Repetir até achar ou a faixa ficar vazia",
                    ],
                ),
                _escolha(
                    4,
                    "Numa lista ordenada de 1.000 itens, quantas comparações a busca "
                    "binária faz, no máximo?",
                    ["Cerca de 10", "1.000", "500", "100"],
                    "Cerca de 10",
                    dica="A cada passo, metade da lista é descartada.",
                ),
                _aberta(
                    5,
                    "Quando vale a pena ordenar a lista para depois usar a busca binária?",
                    "Quando a mesma lista vai ser consultada muitas vezes: o custo de ordenar uma "
                    "vez se paga com buscas muito mais rápidas depois.",
                ),
                _desafio(
                    6,
                    "Implemente a busca binária: a primeira linha traz números inteiros em "
                    "ordem crescente, separados por espaço, e a segunda o alvo. Mostre a "
                    "posição do alvo (a primeira é 0), ou -1 se ele não estiver na lista.",
                    "Guarde o início e o fim da faixa e compare o alvo com o elemento do meio.",
                    [
                        ("1 3 5 7 9\n7\n", "3", True),
                        ("2 4 6\n5\n", "-1", False),
                        ("10\n10\n", "0", False),
                    ],
                ),
            ],
        },
    ],
}

SQL: dict = {
    "slug": "banco-de-dados-sql",
    "nome": "Banco de Dados com SQL",
    "disciplina": "Banco de Dados",
    "categoria": "Dados",
    "periodo": 3,
    "descricao": "Tabelas, consultas, filtros e junções: o básico de SQL para o dia a dia.",
    "modulos": [
        {
            "ordem": 1,
            "titulo": "Tabelas e o modelo relacional",
            "descricao": "Linhas, colunas e chaves: como um banco relacional organiza os dados.",
            "atividades": [
                _escolha(
                    1,
                    "Num banco relacional, o que é uma linha de uma tabela?",
                    ["Um registro", "Um campo", "Um banco", "Uma consulta"],
                    "Um registro",
                ),
                _lacuna(
                    2,
                    "Complete: a coluna que identifica cada linha sem repetir é a chave ___.",
                    "A chave ___ não se repete.",
                    ["primária"],
                    banco=["primária", "estrangeira", "secundária"],
                ),
                _ordenar(
                    3,
                    "Ordene do maior para o menor: banco, tabela, linha, campo.",
                    ["Linha", "Banco", "Campo", "Tabela"],
                    ["Banco", "Tabela", "Linha", "Campo"],
                ),
                _escolha(
                    4,
                    "Para que serve uma chave estrangeira?",
                    [
                        "Ligar uma tabela a outra",
                        "Criptografar a tabela",
                        "Ordenar as linhas",
                        "Apagar registros duplicados",
                    ],
                    "Ligar uma tabela a outra",
                ),
                _aberta(
                    5,
                    "Por que separar alunos e cursos em duas tabelas, e não repetir o curso "
                    "em cada aluno?",
                    "Para não repetir dados: o curso fica numa linha só, cada aluno aponta para "
                    "ela pela chave estrangeira, e mudar o curso muda num lugar só.",
                ),
            ],
        },
        {
            "ordem": 2,
            "titulo": "SELECT e WHERE",
            "descricao": "Busque as colunas que importam e filtre as linhas.",
            "atividades": [
                _escolha(
                    1,
                    "Qual comando lê dados de uma tabela?",
                    ["SELECT", "INSERT", "DELETE", "CREATE"],
                    "SELECT",
                ),
                _lacuna(
                    2,
                    "Complete a consulta dos alunos do 2º período.",
                    "SELECT nome FROM alunos ___ periodo = 2;",
                    ["WHERE"],
                    banco=["WHERE", "ORDER BY", "GROUP BY"],
                ),
                _ordenar(
                    3,
                    "Ordene as partes da consulta.",
                    ["WHERE nota >= 7", "FROM alunos", "SELECT nome"],
                    ["SELECT nome", "FROM alunos", "WHERE nota >= 7"],
                ),
                _escolha(
                    4,
                    "O que SELECT * FROM alunos devolve?",
                    [
                        "Todas as colunas de todas as linhas",
                        "Só a primeira coluna",
                        "Só a quantidade de alunos",
                        "Nada, falta o WHERE",
                    ],
                    "Todas as colunas de todas as linhas",
                ),
                _aberta(
                    5,
                    "Por que é melhor pedir só as colunas necessárias em vez de SELECT *?",
                    "Trafega menos dados, a consulta fica mais rápida e o código não quebra "
                    "quando alguém acrescenta colunas na tabela.",
                ),
            ],
        },
        {
            "ordem": 3,
            "titulo": "Agregações e GROUP BY",
            "descricao": "Conte, some e tire médias por grupo.",
            "atividades": [
                _escolha(
                    1,
                    "Qual função conta as linhas de uma consulta?",
                    ["COUNT", "SUM", "AVG", "MAX"],
                    "COUNT",
                ),
                _lacuna(
                    2,
                    "Complete para contar os alunos de cada período.",
                    "SELECT periodo, COUNT(*) FROM alunos ___ periodo;",
                    ["GROUP BY"],
                    banco=["GROUP BY", "WHERE", "ORDER BY"],
                ),
                _ordenar(
                    3,
                    "Ordene as cláusulas como o SQL exige.",
                    ["GROUP BY curso", "SELECT curso, AVG(nota)", "FROM matriculas"],
                    ["SELECT curso, AVG(nota)", "FROM matriculas", "GROUP BY curso"],
                ),
                _escolha(
                    4,
                    "Para filtrar grupos depois do GROUP BY, usa-se:",
                    ["HAVING", "WHERE", "LIMIT", "JOIN"],
                    "HAVING",
                ),
                _aberta(
                    5,
                    "Qual a diferença entre WHERE e HAVING?",
                    "O WHERE filtra as linhas antes de agrupar; o HAVING filtra os grupos "
                    "depois, e por isso pode usar funções como COUNT e AVG.",
                ),
            ],
        },
        {
            "ordem": 4,
            "titulo": "Juntando tabelas com JOIN",
            "descricao": "Combine linhas de tabelas diferentes pela chave que as liga.",
            "atividades": [
                _escolha(
                    1,
                    "O que o INNER JOIN devolve?",
                    [
                        "Só as linhas que têm par nas duas tabelas",
                        "Todas as linhas das duas tabelas",
                        "Só as linhas da primeira tabela",
                        "As linhas sem par",
                    ],
                    "Só as linhas que têm par nas duas tabelas",
                ),
                _lacuna(
                    2,
                    "Complete a junção de alunos com cursos.",
                    "SELECT a.nome, c.nome\nFROM alunos a\nJOIN cursos c ___ a.curso_id = c.id;",
                    ["ON"],
                    banco=["ON", "WHERE", "AS"],
                ),
                _ordenar(
                    3,
                    "Ordene a consulta que lista cada aluno com o nome do curso.",
                    [
                        "JOIN cursos c ON a.curso_id = c.id",
                        "SELECT a.nome, c.nome",
                        "FROM alunos a",
                    ],
                    [
                        "SELECT a.nome, c.nome",
                        "FROM alunos a",
                        "JOIN cursos c ON a.curso_id = c.id",
                    ],
                ),
                _escolha(
                    4,
                    "Qual JOIN mantém os alunos mesmo sem curso cadastrado?",
                    ["LEFT JOIN", "INNER JOIN", "CROSS JOIN", "Nenhum"],
                    "LEFT JOIN",
                ),
                _aberta(
                    5,
                    "Quando usar LEFT JOIN em vez de INNER JOIN?",
                    "Quando a linha da tabela da esquerda precisa aparecer mesmo sem par na "
                    "outra, como listar todos os alunos, inclusive os sem curso.",
                ),
                _desafio(
                    6,
                    "Com o sqlite3 do Python, crie em memória a tabela alunos (nome, nota). "
                    "Leia um aluno por linha (nome e nota), até uma linha vazia, insira na "
                    "tabela e mostre, com um SELECT, os nomes com nota 7 ou mais, da maior "
                    "nota para a menor.",
                    "sqlite3.connect(':memory:') cria o banco; use WHERE nota >= 7 e "
                    "ORDER BY nota DESC.",
                    [
                        ("Ana 8\nBia 6\nCaio 9.5\n\n", "Caio\nAna", True),
                        ("Duda 5\n\n", "", False),
                        ("Eva 7\nFabi 7.5\n\n", "Fabi\nEva", False),
                    ],
                ),
            ],
        },
    ],
}

TRILHAS = (LOGICA, ESTRUTURAS, SQL)


def aplicar(db: Session) -> list[Trilha]:
    """Grava as três trilhas e devolve-as, na ordem de `TRILHAS`."""
    return [_aplicar_trilha(db, dados) for dados in TRILHAS]


def _aplicar_trilha(db: Session, dados: dict) -> Trilha:
    trilha = db.execute(select(Trilha).where(Trilha.slug == dados["slug"])).scalar_one_or_none()
    if trilha is None:
        trilha = Trilha(slug=dados["slug"])
        db.add(trilha)

    for campo in ("nome", "disciplina", "categoria", "periodo", "descricao"):
        setattr(trilha, campo, dados[campo])
    trilha.publicada = True
    db.flush()

    existentes = {modulo.ordem: modulo for modulo in trilha.modulos}
    for dados_modulo in dados["modulos"]:
        modulo = existentes.get(dados_modulo["ordem"])
        if modulo is None:
            modulo = Modulo(trilha_id=trilha.id, ordem=dados_modulo["ordem"])
            db.add(modulo)
        modulo.titulo = dados_modulo["titulo"]
        modulo.descricao = dados_modulo.get("descricao")
        modulo.video_url = dados_modulo.get("video_url")
        db.flush()

        atividades_existentes = {a.ordem: a for a in modulo.atividades}
        for dados_atividade in dados_modulo["atividades"]:
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
