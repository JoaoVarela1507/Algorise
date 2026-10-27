import { create } from 'zustand'
import { createJSONStorage, devtools, persist } from 'zustand/middleware'
import type { Escolha } from '@/services/onboarding'
import type { NivelExperiencia, TipoTrilha } from '@/types/usuario'

export interface RascunhoOnboarding {
  passo: number
  nivel: NivelExperiencia | null
  trilha: TipoTrilha | null
  instituicao: Escolha
  curso: Escolha
  periodo: string
  ementa: File | null
}

const RASCUNHO_INICIAL: RascunhoOnboarding = {
  passo: 1,
  nivel: null,
  trilha: null,
  instituicao: { texto: '', id: null },
  curso: { texto: '', id: null },
  periodo: '',
  ementa: null,
}

interface OnboardingState {
  /** De quem é o rascunho; ver `vincularAluno`. */
  usuarioId: string | null
  rascunho: RascunhoOnboarding
  salvarRascunho: (rascunho: RascunhoOnboarding) => void
  /** Chamado a cada troca de aluno: o rascunho de outro aluno não vale para este. */
  vincularAluno: (usuarioId: string | null) => void
  limpar: () => void
}

/** Se o aluno já preencheu alguma coisa, e vale voltar para o wizard. */
export function temProgresso(rascunho: RascunhoOnboarding) {
  return rascunho.passo > 1 || rascunho.nivel !== null
}

/**
 * Rascunho do onboarding (telas 7 a 15): sobrevive a voltar para o cadastro e
 * a recarregar a página. Fica no `sessionStorage`, e não no `localStorage`,
 * porque vale só para esta aba: num computador compartilhado, morre com ela.
 */
export const useOnboardingStore = create<OnboardingState>()(
  devtools(
    persist(
      (set, get) => ({
        usuarioId: null,
        rascunho: RASCUNHO_INICIAL,
        salvarRascunho: (rascunho) => set({ rascunho }),
        vincularAluno: (usuarioId) => {
          if (usuarioId !== get().usuarioId) set({ usuarioId, rascunho: RASCUNHO_INICIAL })
        },
        limpar: () => set({ rascunho: RASCUNHO_INICIAL }),
      }),
      {
        name: 'algorise:onboarding',
        storage: createJSONStorage(() => sessionStorage),
        // A ementa é um `File`, que não vira JSON: depois de recarregar, o
        // aluno escolhe o arquivo de novo. O resto volta.
        partialize: ({ usuarioId, rascunho }) => ({
          usuarioId,
          rascunho: { ...rascunho, ementa: null },
        }),
      },
    ),
    { name: 'onboarding', enabled: import.meta.env.DEV },
  ),
)
