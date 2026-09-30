import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { lerPreferencia, salvarPreferencia } from '@/lib/preferencias'

type Tema = 'claro' | 'escuro'
export type PreferenciaTema = Tema | 'sistema'

interface ThemeContextValue {
  /** O tema em uso de fato. */
  tema: Tema
  /** O que o aluno escolheu; "sistema" acompanha o modo do sistema operacional. */
  preferencia: PreferenciaTema
  setPreferencia: (preferencia: PreferenciaTema) => void
  alternarTema: () => void
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined)

const consultaEscuro = '(prefers-color-scheme: dark)'

function sistemaEscuro() {
  return typeof window !== 'undefined' && window.matchMedia(consultaEscuro).matches
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [preferencia, setPreferencia] = useState<PreferenciaTema>(() =>
    lerPreferencia('tema', 'claro'),
  )
  const [escuroNoSistema, setEscuroNoSistema] = useState(sistemaEscuro)

  // Com "sistema", troca junto quando o sistema operacional muda de modo.
  useEffect(() => {
    const consulta = window.matchMedia(consultaEscuro)
    const aoMudar = (evento: MediaQueryListEvent) => setEscuroNoSistema(evento.matches)
    consulta.addEventListener('change', aoMudar)
    return () => consulta.removeEventListener('change', aoMudar)
  }, [])

  const tema: Tema =
    preferencia === 'sistema' ? (escuroNoSistema ? 'escuro' : 'claro') : preferencia

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', tema === 'escuro' ? 'dark' : 'light')
  }, [tema])

  useEffect(() => {
    salvarPreferencia('tema', preferencia)
  }, [preferencia])

  function alternarTema() {
    setPreferencia(tema === 'claro' ? 'escuro' : 'claro')
  }

  return (
    <ThemeContext.Provider value={{ tema, preferencia, setPreferencia, alternarTema }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme deve ser usado dentro de um ThemeProvider')
  }
  return context
}
