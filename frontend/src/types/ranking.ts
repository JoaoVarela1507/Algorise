export interface PosicaoRanking {
  usuarioId: string
  nome: string
  xp: number
  posicao: number
}

export interface TrilhaAtual {
  id: string
  nome: string
  disciplina: string
  modulosConcluidos: number
  totalModulos: number
  proximoModulo: string
}
