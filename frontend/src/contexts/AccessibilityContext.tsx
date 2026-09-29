import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { lerPreferencia, salvarPreferencia } from '@/lib/preferencias'

type TamanhoFonte = 'normal' | 'alta'

interface AccessibilityContextValue {
  tamanhoFonte: TamanhoFonte
  altoContraste: boolean
  /** Desliga as animações do app mesmo que o sistema não peça. */
  reduzirAnimacoes: boolean
  setTamanhoFonte: (tamanho: TamanhoFonte) => void
  setAltoContraste: (ativo: boolean) => void
  setReduzirAnimacoes: (ativo: boolean) => void
}

const AccessibilityContext = createContext<AccessibilityContextValue | undefined>(undefined)

export function AccessibilityProvider({ children }: { children: ReactNode }) {
  const [tamanhoFonte, setTamanhoFonte] = useState<TamanhoFonte>(() =>
    lerPreferencia('tamanho-fonte', 'normal'),
  )
  const [altoContraste, setAltoContraste] = useState(() => lerPreferencia('alto-contraste', false))
  const [reduzirAnimacoes, setReduzirAnimacoes] = useState(() =>
    lerPreferencia('reduzir-animacoes', false),
  )

  useEffect(() => {
    // Os tokens de tema vivem em :root, então o atributo vai no <html>.
    document.documentElement.setAttribute('data-font-size', tamanhoFonte)
    salvarPreferencia('tamanho-fonte', tamanhoFonte)
  }, [tamanhoFonte])

  useEffect(() => {
    document.documentElement.setAttribute('data-high-contrast', String(altoContraste))
    salvarPreferencia('alto-contraste', altoContraste)
  }, [altoContraste])

  useEffect(() => {
    document.documentElement.setAttribute('data-reduzir-animacoes', String(reduzirAnimacoes))
    salvarPreferencia('reduzir-animacoes', reduzirAnimacoes)
  }, [reduzirAnimacoes])

  return (
    <AccessibilityContext.Provider
      value={{
        tamanhoFonte,
        altoContraste,
        reduzirAnimacoes,
        setTamanhoFonte,
        setAltoContraste,
        setReduzirAnimacoes,
      }}
    >
      {children}
    </AccessibilityContext.Provider>
  )
}

export function useAccessibility() {
  const context = useContext(AccessibilityContext)
  if (!context) {
    throw new Error('useAccessibility deve ser usado dentro de um AccessibilityProvider')
  }
  return context
}
