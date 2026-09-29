export type NivelExperiencia = 'baixo' | 'medio' | 'alto'
export type TipoTrilha = 'guiada' | 'livre' | 'mista'

export interface Usuario {
  id: string
  nome: string
  username?: string
  email: string
  avatarUrl?: string
  nivelExperiencia: NivelExperiencia
  tipoTrilha: TipoTrilha
  xp: number
  streakDias: number
  instituicao?: string
  curso?: string
  periodo?: number
}

/** Campos que o aluno pode alterar (perfil e fim do onboarding). */
export type AtualizacaoPerfil = Partial<
  Pick<Usuario, 'nome' | 'nivelExperiencia' | 'tipoTrilha' | 'instituicao' | 'curso' | 'periodo'>
>
