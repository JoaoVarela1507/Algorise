export interface MetaDiaria {
  xpHoje: number
  xpMeta: number
  desafiosResolvidos: number
  minutosEstudados: number
}

/** O ícone sai do `id`, no `ConquistasCard`: a API não fala de desenho. */
export interface Conquista {
  id: string
  titulo: string
  descricao: string
  desbloqueada: boolean
}
