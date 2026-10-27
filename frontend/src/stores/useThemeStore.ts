import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import { lerPreferencia } from '@/lib/preferencias'

type Tema = 'claro' | 'escuro'
export type PreferenciaTema = Tema | 'sistema'

interface ThemeState {
  /** O que o aluno escolheu; "sistema" acompanha o modo do sistema operacional. */
  preferencia: PreferenciaTema
  /** Se o sistema operacional está no modo escuro; só pesa com "sistema". */
  escuroNoSistema: boolean
  setPreferencia: (preferencia: PreferenciaTema) => void
  alternarTema: () => void
}

const consultaEscuro = '(prefers-color-scheme: dark)'

/** O tema em uso de fato. Serve de seletor: `useThemeStore(temaEmUso)`. */
export function temaEmUso({ preferencia, escuroNoSistema }: ThemeState): Tema {
  if (preferencia !== 'sistema') return preferencia
  return escuroNoSistema ? 'escuro' : 'claro'
}

export const useThemeStore = create<ThemeState>()(
  devtools(
    persist(
      (set, get) => ({
        // A chave antiga, de antes do store, para ninguém perder a escolha.
        preferencia: lerPreferencia<PreferenciaTema>('tema', 'claro'),
        escuroNoSistema: window.matchMedia(consultaEscuro).matches,
        setPreferencia: (preferencia) => set({ preferencia }),
        alternarTema: () => set({ preferencia: temaEmUso(get()) === 'claro' ? 'escuro' : 'claro' }),
      }),
      {
        name: 'algorise:aparencia',
        // O modo do sistema é lido de novo a cada visita, não guardado.
        partialize: ({ preferencia }) => ({ preferencia }),
      },
    ),
    { name: 'tema', enabled: import.meta.env.DEV },
  ),
)

// Com "sistema", troca junto quando o sistema operacional muda de modo.
window
  .matchMedia(consultaEscuro)
  .addEventListener('change', (evento) =>
    useThemeStore.setState({ escuroNoSistema: evento.matches }),
  )

function aplicarNoDocumento(estado: ThemeState) {
  document.documentElement.setAttribute(
    'data-theme',
    temaEmUso(estado) === 'escuro' ? 'dark' : 'light',
  )
}

aplicarNoDocumento(useThemeStore.getState())
useThemeStore.subscribe(aplicarNoDocumento)
