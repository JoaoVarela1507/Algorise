import type { AtividadeModulo, ModuloTrilha, TipoAtividade, TrilhaResumo } from '@/types/trilha'

/**
 * Conteúdo de exemplo dos módulos enquanto a trilha não vem da API
 * (`GET /trilhas/{id}` já existe no backend, mas ainda não é chamado aqui).
 */
const titulosPorTrilha: Record<string, [string, string][]> = {
  'introducao-python': [
    ['Primeiros passos', 'O que é Python, como rodar um programa e o famoso print.'],
    ['Variáveis e tipos', 'Guardar valores: números, textos e booleanos.'],
    ['Operadores', 'Contas, comparações e lógica com and, or e not.'],
    ['Entrada e saída', 'Conversar com quem usa o programa com input.'],
    ['Condicionais', 'Tomar decisões com if, elif e else.'],
    ['Laço while', 'Repetir enquanto uma condição for verdadeira.'],
    ['Laço for', 'Percorrer sequências e usar range.'],
    ['Listas', 'Guardar vários valores e percorrê-los.'],
    ['Funções', 'Organizar o código em blocos reutilizáveis.'],
    ['Projeto final', 'Juntar tudo num pequeno programa completo.'],
  ],
  'logica-de-programacao': [
    ['Algoritmos', 'Receitas passo a passo para resolver problemas.'],
    ['Fluxogramas', 'Desenhar o caminho de um algoritmo.'],
    ['Variáveis', 'Onde o algoritmo guarda o que precisa lembrar.'],
    ['Expressões', 'Aritméticas, relacionais e lógicas.'],
    ['Decisão', 'Caminhos diferentes para situações diferentes.'],
    ['Repetição', 'Fazer de novo sem escrever de novo.'],
    ['Vetores', 'Uma variável com várias posições.'],
    ['Matrizes', 'Tabelas de valores em linhas e colunas.'],
    ['Modularização', 'Dividir o problema em partes menores.'],
    ['Desafio final', 'Resolver um problema do começo ao fim.'],
  ],
  'redes-de-computadores': [
    ['Modelo OSI e TCP/IP', 'As camadas que fazem a internet funcionar.'],
    ['Camada física', 'Cabos, sinais e meios de transmissão.'],
    ['Enlace', 'Quadros, MAC e switches.'],
    ['Endereçamento IP', 'IPv4, máscaras e sub-redes.'],
    ['Roteamento', 'Como os pacotes acham o caminho.'],
    ['TCP e UDP', 'Conexão confiável ou entrega rápida.'],
    ['DNS', 'Traduzir nomes em endereços.'],
    ['HTTP', 'A conversa entre navegador e servidor.'],
    ['Segurança em redes', 'Firewalls, TLS e boas práticas.'],
    ['Projeto de rede', 'Planejar uma rede pequena do zero.'],
  ],
}

// Ordem em que os tipos se alternam; a última atividade é sempre o desafio.
const rodizioDeTipos: TipoAtividade[] = [
  'multipla-escolha',
  'preencher-lacuna',
  'ordenacao',
  'terminal',
  'resposta-aberta',
]

const tituloPorTipo: Record<TipoAtividade, (assunto: string) => string> = {
  'multipla-escolha': (assunto) => `Quiz: ${assunto}`,
  'preencher-lacuna': () => 'Complete as lacunas do código',
  ordenacao: () => 'Coloque as linhas na ordem certa',
  terminal: () => 'Pratique no terminal',
  'resposta-aberta': () => 'Explique com suas palavras',
  'desafio-codigo': (assunto) => `Desafio: ${assunto}`,
}

const minutosPorTipo: Record<TipoAtividade, number> = {
  'multipla-escolha': 3,
  'preencher-lacuna': 4,
  ordenacao: 4,
  terminal: 5,
  'resposta-aberta': 5,
  'desafio-codigo': 10,
}

export function atividadesDoModulo(modulo: ModuloTrilha): AtividadeModulo[] {
  return Array.from({ length: modulo.atividades }, (_, i) => {
    const ultima = i === modulo.atividades - 1
    const tipo = ultima
      ? 'desafio-codigo'
      : rodizioDeTipos[(i + modulo.ordem) % rodizioDeTipos.length]
    return {
      id: `${modulo.id}-a${i + 1}`,
      tipo,
      titulo: tituloPorTipo[tipo](modulo.titulo),
      minutos: minutosPorTipo[tipo],
      status:
        modulo.status === 'concluido'
          ? 'feita'
          : modulo.status === 'bloqueado'
            ? 'bloqueada'
            : i === 0
              ? 'proxima'
              : 'pendente',
    }
  })
}

export function modulosDaTrilha(trilha: TrilhaResumo): ModuloTrilha[] {
  const titulos = titulosPorTrilha[trilha.id] ?? []
  return Array.from({ length: trilha.totalModulos }, (_, i) => {
    const [titulo, descricao] = titulos[i] ?? [
      `Módulo ${i + 1}`,
      'Conteúdo e exercícios deste módulo.',
    ]
    return {
      id: `${trilha.id}-${i + 1}`,
      ordem: i + 1,
      titulo,
      descricao,
      atividades: 4 + (i % 3),
      xp: 20 + 5 * Math.floor(i / 3),
      status: trilha.bloqueada
        ? 'bloqueado'
        : i < trilha.modulosConcluidos
          ? 'concluido'
          : i === trilha.modulosConcluidos
            ? 'atual'
            : 'bloqueado',
    }
  })
}
