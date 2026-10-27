import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import { lerPreferencia } from '@/lib/preferencias'

export type TamanhoFonte = 'normal' | 'alta'

interface AccessibilityState {
  tamanhoFonte: TamanhoFonte
  altoContraste: boolean
  /** Desliga as animações do app mesmo que o sistema não peça. */
  reduzirAnimacoes: boolean
  setTamanhoFonte: (tamanho: TamanhoFonte) => void
  setAltoContraste: (ativo: boolean) => void
  setReduzirAnimacoes: (ativo: boolean) => void
}

/**
 * Fonte, contraste e animações (tela 19). Ficam no navegador porque a tela de
 * login abre antes de saber quem é o aluno; a cópia da conta é aplicada ao
 * entrar, pelo `PreferenciasDaConta`.
 */
export const useAccessibilityStore = create<AccessibilityState>()(
  devtools(
    persist(
      (set) => ({
        // Antes do store cada preferência tinha a sua chave: lendo delas, quem
        // já tinha escolhido não perde a escolha na troca.
        tamanhoFonte: lerPreferencia<TamanhoFonte>('tamanho-fonte', 'normal'),
        altoContraste: lerPreferencia('alto-contraste', false),
        reduzirAnimacoes: lerPreferencia('reduzir-animacoes', false),
        setTamanhoFonte: (tamanhoFonte) => set({ tamanhoFonte }),
        setAltoContraste: (altoContraste) => set({ altoContraste }),
        setReduzirAnimacoes: (reduzirAnimacoes) => set({ reduzirAnimacoes }),
      }),
      { name: 'algorise:acessibilidade' },
    ),
    { name: 'acessibilidade', enabled: import.meta.env.DEV },
  ),
)

function aplicarNoDocumento({ tamanhoFonte, altoContraste, reduzirAnimacoes }: AccessibilityState) {
  // Os tokens de tema vivem em :root, então os atributos vão no <html>.
  const html = document.documentElement
  html.setAttribute('data-font-size', tamanhoFonte)
  html.setAttribute('data-high-contrast', String(altoContraste))
  html.setAttribute('data-reduzir-animacoes', String(reduzirAnimacoes))
}

aplicarNoDocumento(useAccessibilityStore.getState())
useAccessibilityStore.subscribe(aplicarNoDocumento)
