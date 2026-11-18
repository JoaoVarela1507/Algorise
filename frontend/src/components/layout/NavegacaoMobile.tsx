import { useEffect, useRef, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { LogOut, Menu, Moon, Sun } from 'lucide-react'
import { CentroNotificacoes } from '@/components/layout/CentroNotificacoes'
import { links } from '@/components/layout/links'
import { versaoCurta } from '@/lib/version'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/useAuthStore'
import { temaEmUso, useThemeStore } from '@/stores/useThemeStore'
import mascote from '@/assets/images/mascote-polvo.png'

/**
 * A navegação no celular: a sidebar de 224px não cabe numa tela de 375px.
 *
 * - `BarraTopo`: o polvo, as notificações e um menu com tema e sair;
 * - `BarraAbas`: as telas principais embaixo, ao alcance do polegar.
 *
 * Do `md` para cima, some, e a `Sidebar` volta.
 */

export function BarraTopo() {
  return (
    // `relative z-30`: o backdrop-blur cria uma camada própria, e sem o z-index o
    // conteúdo da página (desenhado depois) cobria as notificações e o menu.
    <header className="relative z-30 flex items-center justify-between border-b border-border bg-background/95 px-4 py-2 backdrop-blur md:hidden">
      <NavLink to="/" aria-label="Algorise, ir para a Home" className="flex items-center gap-2">
        <img src={mascote} alt="" className="h-8" />
        <span className="font-display text-lg font-bold text-primary">Algorise</span>
      </NavLink>
      <div className="flex items-center gap-1">
        <CentroNotificacoes compacto />
        <MenuConta />
      </div>
    </header>
  )
}

function MenuConta() {
  const [aberto, setAberto] = useState(false)
  const caixaRef = useRef<HTMLDivElement>(null)
  const logout = useAuthStore((estado) => estado.logout)
  const tema = useThemeStore(temaEmUso)
  const alternarTema = useThemeStore((estado) => estado.alternarTema)
  const navigate = useNavigate()

  useEffect(() => {
    if (!aberto) return
    function fora(evento: MouseEvent | TouchEvent) {
      if (!caixaRef.current?.contains(evento.target as Node)) setAberto(false)
    }
    function esc(evento: KeyboardEvent) {
      if (evento.key === 'Escape') setAberto(false)
    }
    document.addEventListener('mousedown', fora)
    document.addEventListener('touchstart', fora)
    document.addEventListener('keydown', esc)
    return () => {
      document.removeEventListener('mousedown', fora)
      document.removeEventListener('touchstart', fora)
      document.removeEventListener('keydown', esc)
    }
  }, [aberto])

  return (
    <div ref={caixaRef} className="relative">
      <button
        type="button"
        onClick={() => setAberto((atual) => !atual)}
        aria-expanded={aberto}
        aria-label="Menu da conta"
        className="flex size-11 items-center justify-center rounded-lg text-foreground transition-colors hover:bg-accent/60"
      >
        <Menu className="size-5" />
      </button>
      <AnimatePresence>
        {aberto && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 top-full z-50 mt-2 flex w-56 flex-col gap-1 rounded-xl border border-border bg-card p-2 shadow-lg"
          >
            <button
              type="button"
              onClick={alternarTema}
              aria-pressed={tema === 'escuro'}
              className="flex items-center gap-2 rounded-lg px-3 py-2.5 font-bold text-card-foreground transition-colors hover:bg-accent/60"
            >
              {tema === 'escuro' ? <Sun className="size-5" /> : <Moon className="size-5" />}
              {tema === 'escuro' ? 'Modo claro' : 'Modo escuro'}
            </button>
            <button
              type="button"
              onClick={() => {
                logout()
                navigate('/boas-vindas')
              }}
              className="flex items-center gap-2 rounded-lg px-3 py-2.5 font-bold text-destructive transition-colors hover:bg-destructive/10"
            >
              <LogOut className="size-5" />
              Sair
            </button>
            <p className="px-3 pt-1 text-xs text-muted-foreground">{versaoCurta}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export function BarraAbas() {
  return (
    <nav
      aria-label="Navegação principal"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-background/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden"
    >
      <ul className="mx-auto flex max-w-md justify-between px-2">
        {links.map(({ to, label, end, icone: Icone }) => (
          <li key={to} className="flex-1">
            <NavLink
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  'flex min-h-14 flex-col items-center justify-center gap-0.5 text-[11px] font-bold transition-colors',
                  isActive ? 'text-primary' : 'text-muted-foreground hover:text-foreground',
                )
              }
            >
              {({ isActive }) => (
                <>
                  <motion.span
                    animate={{ scale: isActive ? 1.12 : 1, y: isActive ? -1 : 0 }}
                    transition={{ type: 'spring', stiffness: 400, damping: 22 }}
                    className={cn(
                      'flex h-7 w-12 items-center justify-center rounded-full',
                      isActive && 'bg-primary/15',
                    )}
                  >
                    <Icone className="size-5" aria-hidden />
                  </motion.span>
                  {/* "Configurações" não cabe em 1/5 da tela. */}
                  {label === 'Configurações' ? 'Ajustes' : label}
                </>
              )}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
