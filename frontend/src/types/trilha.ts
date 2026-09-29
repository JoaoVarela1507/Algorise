export interface Modulo {
  id: string
  titulo: string
  ordem: number
  concluido: boolean
  bloqueado: boolean
}

export interface Trilha {
  id: string
  nome: string
  disciplina: string
  progresso: number
  totalModulos: number
  modulos: Modulo[]
}

export type CategoriaTrilha = 'Linguagens' | 'Gerais' | 'Fundamentos' | 'Infraestrutura' | 'Dados'

/** Versão enxuta da trilha usada na listagem (tela de Trilhas). */
export interface TrilhaResumo {
  id: string
  nome: string
  categoria: CategoriaTrilha
  periodo: number
  modulosConcluidos: number
  totalModulos: number
  /** Por que a trilha aparece para o usuário ("Recomendação do Algorise", "Conhecimentos gerais"…). */
  motivo: string
  recomendada?: boolean
  bloqueada: boolean
  /** Nome da trilha que precisa ser concluída antes, quando bloqueada. */
  requisito?: string
}
