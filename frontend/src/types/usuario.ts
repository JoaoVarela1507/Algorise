export type NivelExperiencia = 'baixo' | 'medio' | 'alto'
export type TipoTrilha = 'guiada' | 'livre' | 'mista'
export type TamanhoFonte = 'normal' | 'alta'

/** Acessibilidade guardada na conta (`PATCH /usuarios/me/preferencias`). */
export interface Preferencias {
  tamanhoFonte: TamanhoFonte
  altoContraste: boolean
  reduzirAnimacoes: boolean
}

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
  /** Ausente quando o perfil não veio da API (login de teste, API fora). */
  preferencias?: Preferencias
  /** Se o aluno já passou pelo onboarding (telas 7 a 15). Ausente fora da API. */
  onboardingConcluido?: boolean
}

/** Campos que o aluno pode alterar (perfil e fim do onboarding). */
export type AtualizacaoPerfil = Partial<
  Pick<Usuario, 'nome' | 'nivelExperiencia' | 'tipoTrilha' | 'instituicao' | 'curso' | 'periodo'>
>
