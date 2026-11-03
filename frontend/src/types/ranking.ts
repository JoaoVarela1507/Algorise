export interface PosicaoRanking {
  usuarioId: string
  nome: string
  xp: number
  posicao: number
}

export interface TrilhaAtual {
  /** O slug: é o que a rota `/trilhas/:trilhaId` recebe. */
  id: string
  nome: string
  disciplina: string
  periodo: number | null
  modulosConcluidos: number
  totalModulos: number
  /** `null` quando a trilha ainda não tem módulo cadastrado. */
  proximoModulo: string | null
}
