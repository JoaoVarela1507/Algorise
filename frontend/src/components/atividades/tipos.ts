import type { AtividadeApi } from '@/services/atividades'

/** O que toda atividade do passo recebe da tela de questão. */
export interface PropsDaAtividade {
  atividade: AtividadeApi
  /** Posição no passo, para a barra "1 de 3". */
  numero: number
  total: number
  /**
   * Chamado no "Avançar", com quantas vezes o aluno errou antes de acertar:
   * é o que o resumo do passo conta como "de primeira" (#22).
   */
  aoAvancar: (errosAntesDeAcertar?: number) => void
}
