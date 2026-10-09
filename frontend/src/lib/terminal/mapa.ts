import { ATIVIDADES, type Atividade } from '@/lib/terminal/roteiro'

/**
 * De qual atividade da API vem cada roteiro de terminal.
 *
 * A API **não manda o gabarito** antes da submissão (#30) — e isso é de
 * propósito: `comando_esperado` no corpo da resposta entregaria o exercício a
 * quem abrisse o devtools. Então o roteiro mora aqui, e esta tabela diz qual
 * roteiro pertence a qual atividade.
 *
 * A chave é a posição — trilha, passo, atividade —, que é estável: a ordem é o
 * que define o caminho da trilha, e mudar a ordem é mudar o exercício de lugar
 * de qualquer jeito.
 *
 * Quando a submissão existir (#30), quem diz se acertou passa a ser o servidor,
 * e este roteiro fica só com o papel de encenar o terminal.
 */
const MAPA: Record<string, Atividade> = {
  'introducao-python:1:1': ATIVIDADES['winget install Python.Python.3.14'],
  'introducao-python:1:2': ATIVIDADES['python --version'],
}

export function roteiroDaAtividade(
  trilhaSlug: string,
  ordemPasso: number,
  ordemAtividade: number,
): Atividade | null {
  return MAPA[`${trilhaSlug}:${ordemPasso}:${ordemAtividade}`] ?? null
}
