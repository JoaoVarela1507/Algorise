import type { LucideIcon } from 'lucide-react'

export interface MetaDiaria {
  xpHoje: number
  xpMeta: number
  desafiosResolvidos: number
  minutosEstudados: number
}

export interface Conquista {
  id: string
  titulo: string
  descricao: string
  icone: LucideIcon
  desbloqueada: boolean
}
