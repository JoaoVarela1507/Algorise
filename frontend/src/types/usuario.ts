export type NivelExperiencia = 'baixo' | 'medio' | 'alto'
export type TipoTrilha = 'guiada' | 'livre' | 'mista'

export interface Usuario {
  id: string
  nome: string
  username?: string
  email: string
  avatarUrl?: string
  /** Conta entra por senha (e não só por GitHub/Google). */
  temSenha?: boolean
  nivelExperiencia: NivelExperiencia
  tipoTrilha: TipoTrilha
  xp: number
  streakDias: number
  instituicao?: string
  curso?: string
  periodo?: number
}
