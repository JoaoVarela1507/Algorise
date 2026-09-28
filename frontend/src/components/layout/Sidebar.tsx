import { NavLink, useNavigate } from 'react-router-dom'
import { LogOut, Moon, Sun } from 'lucide-react'
import { versaoCurta } from '@/lib/version'
import { cn } from '@/lib/utils'
import { useAuth } from '@/contexts/AuthContext'
import { useTheme } from '@/contexts/ThemeContext'
import logoAlgorise from '@/assets/images/logo-algorise.png'

const links = [
  { to: '/', label: 'Home', end: true },
  { to: '/trilhas', label: 'Trilhas' },
  { to: '/chat', label: 'Chat' },
  { to: '/perfil', label: 'Perfil' },
  { to: '/configuracoes', label: 'Configurações' },
]

export function Sidebar() {
  const { logout } = useAuth()
  const { tema, alternarTema } = useTheme()
  const navigate = useNavigate()

  function handleSair() {
    logout()
    navigate('/boas-vindas')
  }

  return (
    <aside className="flex h-screen w-56 flex-col gap-2 bg-accent/40 p-4">
      <img src={logoAlgorise} alt="Algorise" className="mx-auto mb-6 h-28" />
      <nav className="flex flex-col gap-1">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.end}
            className={({ isActive }) =>
              cn(
                'rounded-lg px-4 py-2 font-bold transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-foreground hover:bg-accent/60',
              )
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto flex flex-col gap-2">
        <div className="px-4 text-xs text-muted-foreground" title={`Build ${__APP_BUILD__}`}>
          {versaoCurta}
        </div>

        <button
          type="button"
          onClick={alternarTema}
          aria-pressed={tema === 'escuro'}
          className="flex items-center gap-2 rounded-lg px-4 py-2 font-bold text-foreground transition-colors hover:bg-accent/60"
        >
          {tema === 'escuro' ? <Sun className="size-5" /> : <Moon className="size-5" />}
          {tema === 'escuro' ? 'Modo claro' : 'Modo escuro'}
        </button>

        <button
          type="button"
          onClick={handleSair}
          className="flex items-center gap-2 rounded-lg bg-destructive px-4 py-2 font-bold text-destructive-foreground transition-colors hover:bg-destructive/90"
        >
          <LogOut className="size-5" />
          Sair
        </button>
      </div>
    </aside>
  )
}
