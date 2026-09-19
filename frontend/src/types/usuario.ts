export type NivelExperiencia = 'baixo' | 'medio' | 'alto'
export type TipoTrilha = 'guiada' | 'livre' | 'mista'

export interface Usuario {
  id: string
  nome: string
  email: string
  nivelExperiencia: NivelExperiencia
  tipoTrilha: TipoTrilha
  xp: number
  streakDias: number
  instituicao?: string
  curso?: string
}
