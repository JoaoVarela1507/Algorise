import { NavLink } from 'react-router-dom'
import { versaoCurta } from '@/lib/version'
import { cn } from '@/lib/utils'

const links = [
  { to: '/', label: 'Home', end: true },
  { to: '/trilhas', label: 'Trilhas' },
  { to: '/chat', label: 'Chat' },
  { to: '/perfil', label: 'Perfil' },
]

export function Sidebar() {
  return (
    <aside className="flex h-screen w-56 flex-col gap-2 bg-accent/40 p-4">
      <div className="mb-6 font-display text-2xl font-extrabold text-primary">Algorise</div>
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
      <div
        className="mt-auto px-4 pt-4 text-xs text-muted-foreground"
        title={`Build ${__APP_BUILD__}`}
      >
        {versaoCurta}
      </div>
    </aside>
  )
}
