"""Seed de mais quatro trilhas: Sistemas Operacionais, Engenharia de Software, Web e Recursão.

Seguem o formato das trilhas extras e novas: cada módulo tem 5 atividades (múltipla
escolha, lacuna, ordenação, outra múltipla escolha e resposta aberta) e o último
módulo fecha com o desafio de código, corrigido na sandbox pelos casos de teste.

Idempotente como os outros seeds: a trilha pelo slug, o módulo pela ordem, a
atividade pela ordem dentro do módulo.
"""

from sqlalchemy.orm import Session

from app.models import Trilha
from app.seeds.introducao_python import _aberta, _escolha, _lacuna, _ordenar
from app.seeds.trilhas_extras import _aplicar_trilha, _desafio

SISTEMAS_OPERACIONAIS: dict = {
    "slug": "sistemas-operacionais",
    "nome": "Sistemas Operacionais",
    "disciplina": "Sistemas Operacionais",
    "categoria": "Infraestrutura",
    "periodo": 4,
    "descricao": "Processos, memória, concorrência e escalonamento: o que roda sob o seu programa.",
    "modulos": [
        {
            "ordem": 1,
            "titulo": "O que faz um sistema operacional",
            "descricao": "O intermediário entre os programas e o hardware.",
            "atividades": [
                _escolha(
                    1,
                    "Qual é o papel principal de um sistema operacional?",
                    [
                        "Gerenciar os recursos do computador e dar uma interface aos programas",
                        "Aumentar a velocidade da internet",
                        "Compilar programas em qualquer linguagem",
                        "Substituir o processador",
                    ],
                    "Gerenciar os recursos do computador e dar uma interface aos programas",
                ),
                _lacuna(
                    2,
                    "Complete: o programa pede serviços ao núcleo do sistema por meio de uma "
                    "chamada de ___.",
                    "chamada de ___ (system call)",
                    ["sistema"],
                    banco=["sistema", "função", "rede"],
                ),
                _ordenar(
                    3,
                    "Ordene as camadas, do programa do usuário até o hardware.",
                    [
                        "Hardware",
                        "Núcleo (kernel) do sistema operacional",
                        "Aplicação do usuário",
                    ],
                    [
                        "Aplicação do usuário",
                        "Núcleo (kernel) do sistema operacional",
                        "Hardware",
                    ],
                ),
                _escolha(
                    4,
                    "O que é o kernel?",
                    [
                        "Um antivírus embutido",
                        "O núcleo do sistema operacional, que roda com acesso total ao hardware",
                        "Um tipo de arquivo executável",
                        "A interface gráfica do sistema",
                    ],
                    "O núcleo do sistema operacional, que roda com acesso total ao hardware",
                ),
                _aberta(
                    5,
                    "Por que um programa comum não acessa o disco ou a memória diretamente, "
                    "e sim pede ao sistema operacional?",
                    "Para proteção e organização: o sistema operacional controla quem usa cada "
                    "recurso, evita que um programa corrompa outro ou o próprio sistema e "
                    "esconde os detalhes de cada hardware.",
                ),
            ],
        },
        {
            "ordem": 2,
            "titulo": "Gerência de memória",
            "descricao": "Como vários programas dividem a mesma memória sem se atrapalhar.",
            "atividades": [
                _escolha(
                    1,
                    "O que é memória virtual?",
                    [
                        "Uma memória extra vendida separadamente",
                        "Uma técnica que dá a cada processo um espaço de endereços próprio, "
                        "podendo usar o disco como extensão da RAM",
                        "Uma memória que só existe na nuvem",
                        "Um tipo de cache do processador",
                    ],
                    "Uma técnica que dá a cada processo um espaço de endereços próprio, "
                    "podendo usar o disco como extensão da RAM",
                ),
                _lacuna(
                    2,
                    "Complete: a memória virtual é dividida em blocos de tamanho fixo "
                    "chamados ___.",
                    "A memória é dividida em ___ de tamanho fixo.",
                    ["páginas"],
                    banco=["páginas", "arquivos", "threads"],
                ),
                _ordenar(
                    3,
                    "Ordene o que acontece quando o programa acessa uma página que não está "
                    "na RAM.",
                    [
                        "O programa continua a execução do ponto onde parou",
                        "O sistema carrega a página do disco para a RAM",
                        "Ocorre uma falta de página (page fault)",
                    ],
                    [
                        "Ocorre uma falta de página (page fault)",
                        "O sistema carrega a página do disco para a RAM",
                        "O programa continua a execução do ponto onde parou",
                    ],
                ),
                _escolha(
                    4,
                    "O que é o swap (ou paginação em disco)?",
                    [
                        "Trocar o sistema operacional por outro",
                        "Mover páginas pouco usadas da RAM para o disco para liberar memória",
                        "Compactar arquivos do usuário",
                        "Um erro de acesso à memória",
                    ],
                    "Mover páginas pouco usadas da RAM para o disco para liberar memória",
                ),
                _aberta(
                    5,
                    "Por que o sistema fica muito lento quando a RAM acaba e ele passa a "
                    "usar swap o tempo todo?",
                    "Porque o disco é muito mais lento que a RAM: o sistema gasta o tempo "
                    "trazendo e levando páginas, em vez de executar os programas "
                    "(o chamado thrashing).",
                ),
            ],
        },
        {
            "ordem": 3,
            "titulo": "Concorrência e deadlock",
            "descricao": "Várias linhas de execução disputando os mesmos recursos.",
            "atividades": [
                _escolha(
                    1,
                    "Qual a diferença entre processo e thread?",
                    [
                        "Não há diferença",
                        "O processo tem espaço de memória próprio; as threads de um processo "
                        "compartilham a memória dele",
                        "A thread é sempre mais lenta que o processo",
                        "O processo só existe em sistemas antigos",
                    ],
                    "O processo tem espaço de memória próprio; as threads de um processo "
                    "compartilham a memória dele",
                ),
                _lacuna(
                    2,
                    "Complete: quando duas threads alteram o mesmo dado e o resultado depende "
                    "de quem chega primeiro, temos uma condição de ___.",
                    "condição de ___ (race condition)",
                    ["corrida"],
                    banco=["corrida", "espera", "parada"],
                ),
                _ordenar(
                    3,
                    "Ordene o uso correto de um mutex (trava de exclusão mútua).",
                    [
                        "Liberar o mutex",
                        "Adquirir o mutex",
                        "Usar o recurso compartilhado (seção crítica)",
                    ],
                    [
                        "Adquirir o mutex",
                        "Usar o recurso compartilhado (seção crítica)",
                        "Liberar o mutex",
                    ],
                ),
                _escolha(
                    4,
                    "O que é um deadlock?",
                    [
                        "Quando um processo termina antes do esperado",
                        "Quando processos ficam bloqueados para sempre, cada um esperando um "
                        "recurso que o outro segura",
                        "Quando o disco fica cheio",
                        "Quando a CPU trabalha a 100%",
                    ],
                    "Quando processos ficam bloqueados para sempre, cada um esperando um "
                    "recurso que o outro segura",
                ),
                _aberta(
                    5,
                    "Dê um exemplo do dia a dia que ilustre um deadlock.",
                    "Dois carros em uma ponte estreita, um de cada lado: nenhum recua e "
                    "nenhum passa. Ou duas pessoas, cada uma com um talher, esperando o "
                    "outro talher que a outra segura.",
                ),
            ],
        },
        {
            "ordem": 4,
            "titulo": "Processos e escalonamento",
            "descricao": "Quem usa a CPU agora? O escalonador decide.",
            "atividades": [
                _escolha(
                    1,
                    "O que faz o escalonador (scheduler) do sistema operacional?",
                    [
                        "Escolhe qual processo pronto vai usar a CPU a seguir",
                        "Apaga processos antigos",
                        "Organiza os arquivos em pastas",
                        "Controla a temperatura do processador",
                    ],
                    "Escolhe qual processo pronto vai usar a CPU a seguir",
                ),
                _lacuna(
                    2,
                    "Complete: no escalonamento FCFS, o primeiro processo a chegar é o "
                    "primeiro a ser ___.",
                    "No FCFS, o primeiro a chegar é o primeiro a ser ___.",
                    ["atendido"],
                    banco=["atendido", "removido", "criado"],
                ),
                _ordenar(
                    3,
                    "Ordene os estados de um processo, do início ao fim normal.",
                    [
                        "Terminado",
                        "Em execução",
                        "Novo",
                        "Pronto",
                    ],
                    [
                        "Novo",
                        "Pronto",
                        "Em execução",
                        "Terminado",
                    ],
                ),
                _escolha(
                    4,
                    "No escalonamento Round Robin, o que acontece quando o quantum de um "
                    "processo acaba?",
                    [
                        "O processo é encerrado",
                        "O processo volta para o fim da fila de prontos e o próximo assume a CPU",
                        "O computador reinicia",
                        "O processo ganha prioridade máxima",
                    ],
                    "O processo volta para o fim da fila de prontos e o próximo assume a CPU",
                ),
                _aberta(
                    5,
                    "Qual a desvantagem do FCFS quando um processo muito longo chega "
                    "antes de vários curtos?",
                    "Os processos curtos ficam esperando o longo terminar, o que aumenta "
                    "o tempo médio de espera (o chamado efeito comboio).",
                ),
                _desafio(
                    6,
                    "Simule o escalonamento FCFS. Leia N e, na linha seguinte, os N tempos "
                    "de execução dos processos, na ordem de chegada (todos chegam no "
                    "instante 0). Mostre o tempo médio de espera com duas casas decimais, "
                    "no formato `Espera media: X.XX`. A espera de um processo é a soma dos "
                    "tempos dos que rodaram antes dele.",
                    "Vá acumulando o tempo: a espera de cada processo é o acumulado antes "
                    "dele. Divida a soma das esperas por N e formate com :.2f.",
                    [
                        ("3\n5 3 8\n", "Espera media: 4.33", True),
                        ("1\n10\n", "Espera media: 0.00", False),
                        ("4\n6 8 7 3\n", "Espera media: 10.25", False),
                    ],
                ),
            ],
        },
    ],
}

ENGENHARIA_SOFTWARE: dict = {
    "slug": "engenharia-de-software",
    "nome": "Engenharia de Software",
    "disciplina": "Engenharia de Software",
    "categoria": "Ferramentas",
    "periodo": 5,
    "descricao": "Do requisito à entrega: processos, requisitos, testes e métodos ágeis.",
    "modulos": [
        {
            "ordem": 1,
            "titulo": "Processos de desenvolvimento",
            "descricao": "Cascata, iterativo e ágil: como organizar a construção do software.",
            "atividades": [
                _escolha(
                    1,
                    "Qual é a principal característica do modelo em cascata?",
                    [
                        "As etapas acontecem em sequência, e cada uma só começa quando a "
                        "anterior termina",
                        "O software é entregue a cada dois dias",
                        "Não existe planejamento",
                        "O cliente participa de todas as decisões diárias",
                    ],
                    "As etapas acontecem em sequência, e cada uma só começa quando a "
                    "anterior termina",
                ),
                _lacuna(
                    2,
                    "Complete: os métodos ágeis entregam o software em pequenos ciclos "
                    "chamados ___.",
                    "Ciclos curtos de entrega: ___",
                    ["iterações"],
                    banco=["iterações", "módulos", "versões finais"],
                ),
                _ordenar(
                    3,
                    "Ordene as etapas clássicas do desenvolvimento.",
                    [
                        "Implementação",
                        "Levantamento de requisitos",
                        "Testes",
                        "Projeto (design)",
                    ],
                    [
                        "Levantamento de requisitos",
                        "Projeto (design)",
                        "Implementação",
                        "Testes",
                    ],
                ),
                _escolha(
                    4,
                    "Qual a maior vantagem de um processo ágil sobre o cascata?",
                    [
                        "Dispensa documentação e testes",
                        "Permite receber feedback cedo e adaptar o rumo conforme o projeto avança",
                        "Garante que o projeto nunca atrasa",
                        "Dispensa o cliente",
                    ],
                    "Permite receber feedback cedo e adaptar o rumo conforme o projeto avança",
                ),
                _aberta(
                    5,
                    "Cite um tipo de projeto em que o modelo em cascata ainda faz sentido "
                    "e explique por quê.",
                    "Projetos com requisitos estáveis e bem conhecidos, ou com alto custo de "
                    "erro, como sistemas de aviação ou médicos, em que mudar depois é caro e "
                    "o planejamento detalhado é exigido.",
                ),
            ],
        },
        {
            "ordem": 2,
            "titulo": "Requisitos e histórias de usuário",
            "descricao": "Descobrir o que construir antes de construir.",
            "atividades": [
                _escolha(
                    1,
                    "Qual é um exemplo de requisito não funcional?",
                    [
                        "O sistema deve permitir cadastrar clientes",
                        "O sistema deve responder a qualquer consulta em até 2 segundos",
                        "O usuário pode emitir um relatório em PDF",
                        "O sistema deve enviar e-mail de confirmação",
                    ],
                    "O sistema deve responder a qualquer consulta em até 2 segundos",
                    dica="Requisito não funcional descreve uma qualidade, não uma funcionalidade.",
                ),
                _lacuna(
                    2,
                    "Complete o modelo de história de usuário.",
                    "Como ___, quero enviar um pedido, para receber o produto em casa.",
                    ["cliente"],
                    banco=["cliente", "banco de dados", "servidor"],
                ),
                _ordenar(
                    3,
                    "Ordene as partes de uma história de usuário.",
                    [
                        "para receber o produto em casa",
                        "quero finalizar a compra",
                        "Como cliente",
                    ],
                    [
                        "Como cliente",
                        "quero finalizar a compra",
                        "para receber o produto em casa",
                    ],
                ),
                _escolha(
                    4,
                    "Para que servem os critérios de aceitação de uma história?",
                    [
                        "Para definir o prazo de entrega",
                        "Para dizer objetivamente quando a história está pronta e correta",
                        "Para escolher a linguagem de programação",
                        "Para calcular o salário da equipe",
                    ],
                    "Para dizer objetivamente quando a história está pronta e correta",
                ),
                _aberta(
                    5,
                    "Por que é perigoso começar a programar sem conversar com quem vai usar "
                    "o sistema?",
                    "Porque a equipe pode construir algo que ninguém precisa ou que não "
                    "resolve o problema real, e descobrir isso só no fim, com muito "
                    "retrabalho e custo.",
                ),
            ],
        },
        {
            "ordem": 3,
            "titulo": "Testes e qualidade",
            "descricao": "Como ter confiança de que o software funciona e continua funcionando.",
            "atividades": [
                _escolha(
                    1,
                    "O que é um teste unitário?",
                    [
                        "Um teste feito por um único usuário",
                        "Um teste que verifica uma pequena parte do código, como uma função",
                        "Um teste que só roda em produção",
                        "Um teste feito uma vez por ano",
                    ],
                    "Um teste que verifica uma pequena parte do código, como uma função",
                ),
                _lacuna(
                    2,
                    "Complete a asserção que verifica se soma(2, 3) devolve 5.",
                    "___ soma(2, 3) == 5",
                    ["assert"],
                    banco=["assert", "print", "return"],
                ),
                _ordenar(
                    3,
                    "Ordene a pirâmide de testes, da base (mais testes) ao topo (menos testes).",
                    [
                        "Testes de ponta a ponta (E2E)",
                        "Testes unitários",
                        "Testes de integração",
                    ],
                    [
                        "Testes unitários",
                        "Testes de integração",
                        "Testes de ponta a ponta (E2E)",
                    ],
                    dica="Os testes da base são rápidos e baratos, os do topo são lentos e caros.",
                ),
                _escolha(
                    4,
                    "O que é um teste de regressão?",
                    [
                        "Um teste que verifica que o que já funcionava não quebrou depois "
                        "de uma mudança",
                        "Um teste para usuários antigos",
                        "Um teste que mede o uso de memória",
                        "Um teste feito antes de escrever os requisitos",
                    ],
                    "Um teste que verifica que o que já funcionava não quebrou depois "
                    "de uma mudança",
                ),
                _aberta(
                    5,
                    "Por que rodar os testes automaticamente a cada alteração (integração "
                    "contínua) ajuda a equipe?",
                    "Porque os erros aparecem logo depois de serem introduzidos, quando é "
                    "fácil achar a causa e corrigir, e a equipe tem confiança para mudar "
                    "o código sem medo de quebrar algo.",
                ),
            ],
        },
        {
            "ordem": 4,
            "titulo": "Scrum e planejamento",
            "descricao": "Sprints, backlog e velocidade da equipe.",
            "atividades": [
                _escolha(
                    1,
                    "O que é o product backlog no Scrum?",
                    [
                        "A lista priorizada de tudo o que se quer construir no produto",
                        "O relatório de erros do servidor",
                        "A reunião diária da equipe",
                        "O código-fonte do projeto",
                    ],
                    "A lista priorizada de tudo o que se quer construir no produto",
                ),
                _lacuna(
                    2,
                    "Complete: o período fixo em que a equipe entrega um incremento do "
                    "produto chama-se ___.",
                    "Um período fixo de trabalho no Scrum: ___",
                    ["sprint"],
                    banco=["sprint", "release", "commit"],
                ),
                _ordenar(
                    3,
                    "Ordene as cerimônias de uma sprint.",
                    [
                        "Retrospectiva da sprint",
                        "Planejamento da sprint",
                        "Revisão da sprint (demonstração)",
                        "Execução, com reuniões diárias",
                    ],
                    [
                        "Planejamento da sprint",
                        "Execução, com reuniões diárias",
                        "Revisão da sprint (demonstração)",
                        "Retrospectiva da sprint",
                    ],
                ),
                _escolha(
                    4,
                    "O que é a velocidade (velocity) de uma equipe?",
                    [
                        "A rapidez com que cada pessoa digita",
                        "Quantos pontos de história a equipe costuma entregar por sprint",
                        "O tempo de resposta do sistema",
                        "O número de commits por dia",
                    ],
                    "Quantos pontos de história a equipe costuma entregar por sprint",
                ),
                _aberta(
                    5,
                    "Para que serve a retrospectiva ao final da sprint?",
                    "Para a equipe conversar sobre o que deu certo, o que deu errado e o que "
                    "pode melhorar no jeito de trabalhar, definindo ações para a próxima "
                    "sprint.",
                ),
                _desafio(
                    6,
                    "Planeje as sprints restantes. Na primeira linha vem o total de pontos "
                    "que faltam no backlog; na segunda, os pontos entregues nas sprints "
                    "passadas, separados por espaço. Mostre `Velocidade: X.X` (média, com "
                    "uma casa decimal) e `Sprints restantes: N`, com N sendo o menor número "
                    "inteiro de sprints necessário para entregar o backlog mantendo a "
                    "velocidade média.",
                    "Calcule a média com sum/len e use math.ceil(backlog / media) para "
                    "arredondar para cima.",
                    [
                        ("50\n8 12 10\n", "Velocidade: 10.0\nSprints restantes: 5", True),
                        ("35\n10 10\n", "Velocidade: 10.0\nSprints restantes: 4", False),
                        ("20\n3 4\n", "Velocidade: 3.5\nSprints restantes: 6", False),
                    ],
                ),
            ],
        },
    ],
}

WEB: dict = {
    "slug": "desenvolvimento-web-html-css-http",
    "nome": "Desenvolvimento Web: HTML, CSS e HTTP",
    "disciplina": "Desenvolvimento Web",
    "categoria": "Linguagens",
    "periodo": 3,
    "descricao": "A base de toda página: estrutura em HTML, estilo em CSS e a conversa HTTP.",
    "modulos": [
        {
            "ordem": 1,
            "titulo": "HTML: a estrutura da página",
            "descricao": "Marcação que diz ao navegador o que cada pedaço do conteúdo é.",
            "atividades": [
                _escolha(
                    1,
                    "Para que serve o HTML?",
                    [
                        "Para definir a estrutura e o significado do conteúdo da página",
                        "Para guardar dados em um banco",
                        "Para executar cálculos no servidor",
                        "Para proteger a página contra ataques",
                    ],
                    "Para definir a estrutura e o significado do conteúdo da página",
                ),
                _lacuna(
                    2,
                    "Complete a tag que cria um link para outra página.",
                    '<___ href="https://exemplo.com">Visitar</___>',
                    ["a", "a"],
                    banco=["a", "link", "href"],
                ),
                _ordenar(
                    3,
                    "Ordene as linhas de um documento HTML básico.",
                    [
                        "</html>",
                        "<body><h1>Olá</h1></body>",
                        "<html>",
                        "<head><title>Minha página</title></head>",
                    ],
                    [
                        "<html>",
                        "<head><title>Minha página</title></head>",
                        "<body><h1>Olá</h1></body>",
                        "</html>",
                    ],
                ),
                _escolha(
                    4,
                    "Qual tag representa o título principal da página?",
                    ["<h1>", "<p>", "<title>", "<header>"],
                    "<h1>",
                ),
                _aberta(
                    5,
                    "Por que usar tags com significado (como <nav>, <article> e <footer>) "
                    "em vez de só <div>?",
                    "Elas descrevem o papel de cada parte da página, o que ajuda leitores de "
                    "tela, buscadores e quem mantém o código a entender a estrutura.",
                ),
            ],
        },
        {
            "ordem": 2,
            "titulo": "CSS: estilo e layout",
            "descricao": "Cores, espaçamentos e posição: a aparência da página.",
            "atividades": [
                _escolha(
                    1,
                    "Qual é a função do CSS?",
                    [
                        "Controlar a aparência da página: cores, fontes e layout",
                        "Buscar dados no servidor",
                        "Criar a estrutura dos parágrafos",
                        "Compilar o código JavaScript",
                    ],
                    "Controlar a aparência da página: cores, fontes e layout",
                ),
                _lacuna(
                    2,
                    "Complete a regra que deixa todos os parágrafos com texto azul.",
                    "p { ___: blue; }",
                    ["color"],
                    banco=["color", "text", "background"],
                ),
                _ordenar(
                    3,
                    "Ordene as partes de uma regra CSS.",
                    [
                        "color: red;",
                        "h1 {",
                        "}",
                    ],
                    [
                        "h1 {",
                        "color: red;",
                        "}",
                    ],
                ),
                _escolha(
                    4,
                    "No modelo de caixa (box model), de dentro para fora, qual é a ordem?",
                    [
                        "Conteúdo, padding, borda, margin",
                        "Margin, borda, padding, conteúdo",
                        "Borda, conteúdo, margin, padding",
                        "Padding, conteúdo, margin, borda",
                    ],
                    "Conteúdo, padding, borda, margin",
                ),
                _aberta(
                    5,
                    "Qual a vantagem de colocar o CSS em um arquivo separado em vez de "
                    "repetir os estilos em cada tag?",
                    "O mesmo arquivo estiliza todas as páginas, então mudar o visual é "
                    "alterar um só lugar; o HTML fica mais limpo e o navegador reaproveita "
                    "o arquivo em cache.",
                ),
            ],
        },
        {
            "ordem": 3,
            "titulo": "HTTP: a conversa entre navegador e servidor",
            "descricao": "Pedido e resposta: como a web realmente funciona.",
            "atividades": [
                _escolha(
                    1,
                    "Como funciona o protocolo HTTP?",
                    [
                        "O cliente envia uma requisição e o servidor devolve uma resposta",
                        "O servidor envia dados sem ninguém pedir",
                        "Os computadores trocam arquivos só por e-mail",
                        "O navegador guarda tudo e nunca fala com o servidor",
                    ],
                    "O cliente envia uma requisição e o servidor devolve uma resposta",
                ),
                _lacuna(
                    2,
                    "Complete o método HTTP usado para buscar uma página ou um dado.",
                    "___ /produtos HTTP/1.1",
                    ["GET"],
                    banco=["GET", "POST", "DELETE"],
                ),
                _ordenar(
                    3,
                    "Ordene o que acontece ao abrir um endereço no navegador.",
                    [
                        "O navegador mostra a página",
                        "O servidor devolve a resposta com o HTML",
                        "O navegador envia a requisição ao servidor",
                        "O navegador descobre o IP do domínio (DNS)",
                    ],
                    [
                        "O navegador descobre o IP do domínio (DNS)",
                        "O navegador envia a requisição ao servidor",
                        "O servidor devolve a resposta com o HTML",
                        "O navegador mostra a página",
                    ],
                ),
                _escolha(
                    4,
                    "Qual método HTTP costuma ser usado para criar um novo recurso?",
                    ["POST", "GET", "HEAD", "OPTIONS"],
                    "POST",
                ),
                _aberta(
                    5,
                    "Qual a diferença entre HTTP e HTTPS?",
                    "O HTTPS é o HTTP com criptografia (TLS): os dados trafegam protegidos "
                    "contra leitura e alteração no caminho, e o navegador confirma a "
                    "identidade do site por certificado.",
                ),
            ],
        },
        {
            "ordem": 4,
            "titulo": "Códigos de status e APIs",
            "descricao": "O que o servidor quer dizer com 200, 404 ou 500.",
            "atividades": [
                _escolha(
                    1,
                    "O que significa o código de status 404?",
                    [
                        "O recurso pedido não foi encontrado",
                        "A requisição deu certo",
                        "Erro interno no servidor",
                        "O usuário não está autorizado",
                    ],
                    "O recurso pedido não foi encontrado",
                ),
                _lacuna(
                    2,
                    "Complete: a classe de códigos 5xx indica erro do ___.",
                    "Códigos 5xx: erro do ___",
                    ["servidor"],
                    banco=["servidor", "cliente", "navegador"],
                ),
                _ordenar(
                    3,
                    "Ordene as classes de status, de 1xx a 5xx, pelo significado.",
                    [
                        "4xx: erro do cliente",
                        "2xx: sucesso",
                        "5xx: erro do servidor",
                        "3xx: redirecionamento",
                    ],
                    [
                        "2xx: sucesso",
                        "3xx: redirecionamento",
                        "4xx: erro do cliente",
                        "5xx: erro do servidor",
                    ],
                ),
                _escolha(
                    4,
                    "Qual formato de dados as APIs web mais usam para trocar informações?",
                    ["JSON", "BMP", "MP3", "EXE"],
                    "JSON",
                ),
                _aberta(
                    5,
                    "Por que é importante a API devolver o código de status certo (e não "
                    "sempre 200)?",
                    "Porque quem consome a API usa o status para saber se deu certo ou o que "
                    "falhou e reagir de forma correta, sem precisar adivinhar lendo o texto "
                    "da resposta.",
                ),
                _desafio(
                    6,
                    "Classifique códigos de status HTTP. Leia N e, em seguida, N linhas, "
                    "cada uma com um código. Para cada um mostre `codigo classe`, em que a "
                    "classe é: `Sucesso` (200 a 299), `Redirecionamento` (300 a 399), "
                    "`Erro do cliente` (400 a 499), `Erro do servidor` (500 a 599) ou "
                    "`Invalido` para qualquer outro valor.",
                    "Use comparações encadeadas, como 200 <= codigo <= 299, e deixe o "
                    "else para o Invalido.",
                    [
                        (
                            "3\n200\n404\n500\n",
                            "200 Sucesso\n404 Erro do cliente\n500 Erro do servidor",
                            True,
                        ),
                        (
                            "4\n301\n503\n99\n204\n",
                            "301 Redirecionamento\n503 Erro do servidor\n99 Invalido\n204 Sucesso",
                            False,
                        ),
                        ("2\n600\n418\n", "600 Invalido\n418 Erro do cliente", False),
                    ],
                ),
            ],
        },
    ],
}

RECURSAO: dict = {
    "slug": "recursao-e-programacao-funcional-em-python",
    "nome": "Recursão e Programação Funcional em Python",
    "disciplina": "Paradigmas de Programação",
    "categoria": "Linguagens",
    "periodo": 2,
    "descricao": "Funções que chamam a si mesmas, map, filter, lambda e comprehensions.",
    "modulos": [
        {
            "ordem": 1,
            "titulo": "Pensando recursivamente",
            "descricao": "Resolver um problema grande usando uma versão menor dele mesmo.",
            "atividades": [
                _escolha(
                    1,
                    "O que é uma função recursiva?",
                    [
                        "Uma função que chama a si mesma",
                        "Uma função que nunca termina",
                        "Uma função sem parâmetros",
                        "Uma função escrita em outro arquivo",
                    ],
                    "Uma função que chama a si mesma",
                ),
                _lacuna(
                    2,
                    "Complete o caso base do fatorial.",
                    "def fatorial(n):\n    if n == ___:\n        return 1\n"
                    "    return n * fatorial(n - 1)",
                    ["0"],
                    banco=["0", "10", "-1"],
                ),
                _ordenar(
                    3,
                    "Ordene as linhas da função recursiva que soma de 1 até n.",
                    [
                        "    return n + soma(n - 1)",
                        "def soma(n):",
                        "        return 0",
                        "    if n == 0:",
                    ],
                    [
                        "def soma(n):",
                        "    if n == 0:",
                        "        return 0",
                        "    return n + soma(n - 1)",
                    ],
                ),
                _escolha(
                    4,
                    "O que acontece se uma função recursiva não tiver caso base?",
                    [
                        "Ela devolve 0",
                        "Ela chama a si mesma sem parar e causa RecursionError",
                        "O Python corrige sozinho",
                        "Ela roda uma única vez",
                    ],
                    "Ela chama a si mesma sem parar e causa RecursionError",
                ),
                _aberta(
                    5,
                    "Explique com suas palavras o que são o caso base e o passo recursivo.",
                    "O caso base é a situação mais simples, resolvida direto, que encerra a "
                    "recursão. O passo recursivo reduz o problema a uma versão menor e "
                    "chama a própria função, aproximando-se do caso base.",
                ),
            ],
        },
        {
            "ordem": 2,
            "titulo": "Recursão em listas e memoização",
            "descricao": "Percorrer sequências recursivamente e evitar trabalho repetido.",
            "atividades": [
                _escolha(
                    1,
                    "Em uma função recursiva que soma os elementos de uma lista, qual é o "
                    "caso base natural?",
                    [
                        "A lista vazia, cuja soma é 0",
                        "A lista com mil elementos",
                        "O primeiro elemento ser zero",
                        "A lista ter números negativos",
                    ],
                    "A lista vazia, cuja soma é 0",
                ),
                _lacuna(
                    2,
                    "Complete o passo recursivo: o primeiro elemento mais a soma do resto.",
                    "def soma(lista):\n    if not lista:\n        return 0\n"
                    "    return lista[0] + soma(lista[___])",
                    ["1:"],
                    banco=["1:", ":1", "-1"],
                ),
                _ordenar(
                    3,
                    "Ordene o cálculo recursivo de fib(3), da chamada inicial ao resultado.",
                    [
                        "fib(2) + fib(1)",
                        "(fib(1) + fib(0)) + fib(1)",
                        "(1 + 0) + 1",
                        "2",
                        "fib(3)",
                    ],
                    [
                        "fib(3)",
                        "fib(2) + fib(1)",
                        "(fib(1) + fib(0)) + fib(1)",
                        "(1 + 0) + 1",
                        "2",
                    ],
                ),
                _escolha(
                    4,
                    "Para que serve a memoização (por exemplo, com functools.cache)?",
                    [
                        "Guardar os resultados já calculados para não repeti-los",
                        "Apagar variáveis que não são mais usadas",
                        "Converter recursão em um erro",
                        "Imprimir o resultado na tela",
                    ],
                    "Guardar os resultados já calculados para não repeti-los",
                ),
                _aberta(
                    5,
                    "Por que o fibonacci recursivo simples fica lentíssimo para n grande, "
                    "e como a memoização resolve?",
                    "Porque ele recalcula os mesmos valores muitas vezes, com crescimento "
                    "exponencial de chamadas. Com memoização cada valor é calculado uma só "
                    "vez e reaproveitado.",
                ),
            ],
        },
        {
            "ordem": 3,
            "titulo": "Funções como valores",
            "descricao": "lambda, map e filter: passar funções para outras funções.",
            "atividades": [
                _escolha(
                    1,
                    "O que é uma função lambda em Python?",
                    [
                        "Uma função anônima, escrita em uma única expressão",
                        "Uma função que só funciona com listas",
                        "Um módulo da biblioteca padrão",
                        "Uma função recursiva obrigatória",
                    ],
                    "Uma função anônima, escrita em uma única expressão",
                ),
                _lacuna(
                    2,
                    "Complete para obter o dobro de cada número da lista.",
                    "dobros = list(___(lambda x: x * 2, [1, 2, 3]))",
                    ["map"],
                    banco=["map", "filter", "sum"],
                ),
                _ordenar(
                    3,
                    "Ordene as linhas para ficar só com os números pares e somá-los.",
                    [
                        "print(sum(pares))",
                        "numeros = [1, 2, 3, 4, 5, 6]",
                        "pares = filter(lambda x: x % 2 == 0, numeros)",
                    ],
                    [
                        "numeros = [1, 2, 3, 4, 5, 6]",
                        "pares = filter(lambda x: x % 2 == 0, numeros)",
                        "print(sum(pares))",
                    ],
                ),
                _escolha(
                    4,
                    "O que faz filter(f, itens)?",
                    [
                        "Mantém só os itens para os quais f devolve verdadeiro",
                        "Aplica f a todos os itens e devolve os resultados",
                        "Ordena os itens usando f",
                        "Remove os itens duplicados",
                    ],
                    "Mantém só os itens para os quais f devolve verdadeiro",
                ),
                _aberta(
                    5,
                    "O que significa dizer que funções são 'cidadãs de primeira classe' em Python?",
                    "Que funções são valores como quaisquer outros: podem ser guardadas em "
                    "variáveis, passadas como argumento e devolvidas por outras funções.",
                ),
            ],
        },
        {
            "ordem": 4,
            "titulo": "Comprehensions e estilo funcional",
            "descricao": "Transformar dados de forma curta, clara e sem efeitos colaterais.",
            "atividades": [
                _escolha(
                    1,
                    "O que a expressão [x * x for x in range(4)] produz?",
                    ["[0, 1, 4, 9]", "[1, 4, 9, 16]", "[0, 1, 2, 3]", "[0, 2, 4, 6]"],
                    "[0, 1, 4, 9]",
                ),
                _lacuna(
                    2,
                    "Complete a comprehension que filtra só os números pares.",
                    "pares = [x for x in range(10) ___ x % 2 == 0]",
                    ["if"],
                    banco=["if", "while", "else"],
                ),
                _ordenar(
                    3,
                    "Ordene as etapas de um pipeline funcional: de uma lista de números "
                    "ao total dos quadrados dos ímpares.",
                    [
                        "Somar os quadrados",
                        "Elevar cada ímpar ao quadrado",
                        "Manter só os números ímpares",
                    ],
                    [
                        "Manter só os números ímpares",
                        "Elevar cada ímpar ao quadrado",
                        "Somar os quadrados",
                    ],
                ),
                _escolha(
                    4,
                    "O que é uma função pura?",
                    [
                        "Uma função que, para as mesmas entradas, devolve sempre o mesmo "
                        "resultado e não altera nada fora dela",
                        "Uma função sem nome",
                        "Uma função que usa variáveis globais",
                        "Uma função que imprime na tela",
                    ],
                    "Uma função que, para as mesmas entradas, devolve sempre o mesmo "
                    "resultado e não altera nada fora dela",
                ),
                _aberta(
                    5,
                    "Cite uma vantagem de funções puras para testar e entender o código.",
                    "Como o resultado depende só das entradas, o teste é simples (basta "
                    "comparar entrada e saída), não há surpresas de estado escondido e a "
                    "função pode ser reutilizada em qualquer lugar.",
                ),
                _desafio(
                    6,
                    "Escreva duas funções recursivas. Leia um inteiro n (n >= 0) e mostre "
                    "`Fatorial: x` com o fatorial de n e `Fibonacci: y` com o n-ésimo "
                    "número de Fibonacci, considerando fib(0) = 0 e fib(1) = 1.",
                    "O caso base do fatorial é n == 0; o do Fibonacci é n < 2. Para n "
                    "pequeno, a recursão simples basta.",
                    [
                        ("5\n", "Fatorial: 120\nFibonacci: 5", True),
                        ("0\n", "Fatorial: 1\nFibonacci: 0", False),
                        ("10\n", "Fatorial: 3628800\nFibonacci: 55", False),
                    ],
                ),
            ],
        },
    ],
}

TRILHAS = (SISTEMAS_OPERACIONAIS, ENGENHARIA_SOFTWARE, WEB, RECURSAO)


def aplicar(db: Session) -> list[Trilha]:
    """Grava as quatro trilhas e devolve-as, na ordem de `TRILHAS`."""
    return [_aplicar_trilha(db, dados) for dados in TRILHAS]
