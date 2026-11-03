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

/**
 * `atual` é o primeiro passo aberto que falta, onde o polvo fica; `disponivel`,
 * os outros abertos (no modo livre, por exemplo, tudo abre de uma vez).
 */
export type StatusModulo = 'concluido' | 'atual' | 'disponivel' | 'bloqueado'

/** Um módulo como o mapa da trilha o mostra. */
export interface ModuloTrilha {
  id: string
  ordem: number
  titulo: string
  descricao: string
  atividades: AtividadeModulo[]
  xp: number
  status: StatusModulo
}

/** A trilha da tela 26: o cabeçalho, o mapa e o resumo. */
export interface TrilhaComModulos extends TrilhaResumo {
  disciplina: string
  /** Só trilha de parceiro emite certificado. */
  parceiro: string | null
  modulos: ModuloTrilha[]
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
