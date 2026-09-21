import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

type TamanhoFonte = 'normal' | 'alta'

interface AccessibilityContextValue {
  tamanhoFonte: TamanhoFonte
  altoContraste: boolean
  setTamanhoFonte: (tamanho: TamanhoFonte) => void
  setAltoContraste: (ativo: boolean) => void
}

const AccessibilityContext = createContext<AccessibilityContextValue | undefined>(undefined)

export function AccessibilityProvider({ children }: { children: ReactNode }) {
  const [tamanhoFonte, setTamanhoFonte] = useState<TamanhoFonte>('normal')
  const [altoContraste, setAltoContraste] = useState(false)

  useEffect(() => {
    // Os tokens de tema vivem em :root, então o atributo vai no <html>.
    document.documentElement.setAttribute('data-font-size', tamanhoFonte)
  }, [tamanhoFonte])

  useEffect(() => {
    document.documentElement.setAttribute('data-high-contrast', String(altoContraste))
  }, [altoContraste])

  return (
    <AccessibilityContext.Provider
      value={{ tamanhoFonte, altoContraste, setTamanhoFonte, setAltoContraste }}
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
