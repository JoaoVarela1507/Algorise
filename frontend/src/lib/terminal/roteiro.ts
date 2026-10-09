/**
 * O que o terminal simulado responde a cada comando (telas 28 a 33).
 *
 * Fica separado do componente de propósito: aqui não há DOM nem Xterm, só
 * entrada de texto e saída de texto. Isso deixa a regra testável sem montar
 * nada e, mais importante, deixa claro o que é **simulação** — o `winget` não
 * instala Python nenhum.
 *
 * A correção que vale XP é a do servidor (#30). O roteiro daqui existe para o
 * aluno sentir que está num terminal de verdade: ele erra, lê a mensagem, tenta
 * de novo. A resposta final continua sendo conferida pela API.
 */

export type TipoLinha = 'comando' | 'saida' | 'erro' | 'sucesso'

export interface Linha {
  tipo: TipoLinha
  texto: string
  /** Milissegundos a esperar antes de escrever esta linha, para simular trabalho. */
  atraso?: number
}

export interface Resultado {
  linhas: Linha[]
  /** Se o comando era o que a atividade pedia. */
  acertou: boolean
}

export interface Atividade {
  /** O que a atividade pede. A comparação ignora espaço sobrando e maiúsculas. */
  comandoEsperado: string
  /** Saída de sucesso, já roteirizada. */
  sucesso: Linha[]
  /** Erros com resposta própria, como um comando quase certo (`python ---version`). */
  erros?: { comando: string; linhas: Linha[] }[]
}

/** Prompt do `cmd` do Windows, que é o terminal do protótipo. */
export const PROMPT = 'C:\\Users\\aluno>'

/**
 * Normaliza antes de comparar: o aluno digita `  python   --version  ` e isso é
 * o mesmo comando. Não mexe no que está entre aspas porque nenhum comando das
 * atividades usa aspas; quando usar, isto aqui precisa crescer.
 */
export function normalizar(comando: string): string {
  return comando.trim().replace(/\s+/g, ' ').toLowerCase()
}

export const ATIVIDADES: Record<string, Atividade> = {
  // Tela 28 a 30: instalar o Python.
  'winget install Python.Python.3.14': {
    comandoEsperado: 'winget install Python.Python.3.14',
    sucesso: [
      { tipo: 'saida', texto: 'Encontrado Python 3.14 [Python.Python.3.14] Versão 3.14.0' },
      { tipo: 'saida', texto: 'Baixando https://python.org/ftp/python/3.14.0/python-3.14.0.exe' },
      { tipo: 'saida', texto: '  ██████░░░░░░░░░░░░░░░░░░░░░░░░  18%', atraso: 400 },
      { tipo: 'saida', texto: '  ██████████████░░░░░░░░░░░░░░░░  47%', atraso: 500 },
      { tipo: 'saida', texto: '  ████████████████████████░░░░░░  81%', atraso: 500 },
      { tipo: 'saida', texto: '  ██████████████████████████████ 100%', atraso: 400 },
      { tipo: 'saida', texto: 'Hash verificado com êxito', atraso: 300 },
      { tipo: 'saida', texto: 'Iniciando a instalação do pacote...', atraso: 300 },
      { tipo: 'sucesso', texto: 'Instalação concluída com êxito', atraso: 600 },
    ],
  },

  // Tela 31 a 33: conferir a versão instalada.
  'python --version': {
    comandoEsperado: 'python --version',
    sucesso: [{ tipo: 'sucesso', texto: 'Python 3.14.0' }],
    erros: [
      {
        // O erro que o protótipo mostra: três hifens em vez de dois.
        comando: 'python ---version',
        linhas: [
          { tipo: 'erro', texto: 'unknown option ---version' },
          { tipo: 'saida', texto: 'usage: python [option] ... [-c cmd | -m mod | file | -] [arg]' },
          { tipo: 'saida', texto: 'Try `python -h` for more information.' },
        ],
      },
    ],
  },
}

/** Saída de quem digitou algo que o `cmd` não conhece. */
function desconhecido(comando: string): Linha[] {
  return [
    {
      tipo: 'erro',
      texto:
        `'${comando.trim().split(' ')[0]}' não é reconhecido como um comando interno` +
        ' ou externo, um programa operável ou um arquivo em lotes.',
    },
  ]
}

/** Comandos que funcionam em qualquer atividade, porque o aluno vai tentar. */
const UNIVERSAIS: Record<string, Linha[]> = {
  'python -h': [
    { tipo: 'saida', texto: 'usage: python [option] ... [-c cmd | -m mod | file | -] [arg]' },
    { tipo: 'saida', texto: 'Options:' },
    { tipo: 'saida', texto: '  -V, --version   print the Python version number and exit' },
    { tipo: 'saida', texto: '  -h, --help      print this help message and exit' },
  ],
  help: [
    { tipo: 'saida', texto: 'Este é um terminal simulado do Algorise.' },
    { tipo: 'saida', texto: 'Digite o comando que a atividade pede para continuar.' },
  ],
}

/**
 * Roda um comando contra a atividade e devolve o que o terminal deve escrever.
 *
 * `cls` e `limpar` não aparecem aqui: limpar a tela é coisa do componente, não
 * do roteiro, e ele trata antes de chegar nesta função.
 */
export function executar(comando: string, atividade: Atividade): Resultado {
  const digitado = normalizar(comando)

  if (!digitado) {
    return { linhas: [], acertou: false }
  }

  if (digitado === normalizar(atividade.comandoEsperado)) {
    return { linhas: atividade.sucesso, acertou: true }
  }

  const erroRoteirizado = atividade.erros?.find((erro) => normalizar(erro.comando) === digitado)
  if (erroRoteirizado) {
    return { linhas: erroRoteirizado.linhas, acertou: false }
  }

  const universal = UNIVERSAIS[digitado]
  if (universal) {
    return { linhas: universal, acertou: false }
  }

  return { linhas: desconhecido(comando), acertou: false }
}
