import type { AtividadeApi } from '@/services/atividades'

/** O que toda atividade do passo recebe da tela de questão. */
export interface PropsDaAtividade {
  atividade: AtividadeApi
  /** Posição no passo, para a barra "1 de 3". */
  numero: number
  total: number
  aoAvancar: () => void
}
