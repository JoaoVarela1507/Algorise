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
