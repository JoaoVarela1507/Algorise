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

export type StatusModulo = 'concluido' | 'atual' | 'bloqueado'

/** Um módulo como o mapa da trilha o mostra. */
export interface ModuloTrilha {
  id: string
  ordem: number
  titulo: string
  descricao: string
  atividades: number
  xp: number
  status: StatusModulo
}

/** Mesmos valores do `TipoAtividade` do backend (telas 28 a 34). */
export type TipoAtividade =
  | 'multipla-escolha'
  | 'ordenacao'
  | 'preencher-lacuna'
  | 'terminal'
  | 'resposta-aberta'
  | 'desafio-codigo'

export type StatusAtividade = 'feita' | 'proxima' | 'pendente' | 'bloqueada'

export interface AtividadeModulo {
  id: string
  tipo: TipoAtividade
  titulo: string
  minutos: number
  status: StatusAtividade
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
