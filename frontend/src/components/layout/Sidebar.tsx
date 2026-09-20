import { NavLink } from 'react-router-dom'
import { versaoCurta } from '@/lib/version'

const links = [
  { to: '/', label: 'Home', end: true },
  { to: '/trilhas', label: 'Trilhas' },
  { to: '/chat', label: 'Chat' },
  { to: '/perfil', label: 'Perfil' },
]

export function Sidebar() {
  return (
    <aside className="flex h-screen w-56 flex-col gap-2 bg-salmon-light/40 p-4">
      <div className="mb-6 text-2xl font-extrabold text-salmon">Algorise</div>
      <nav className="flex flex-col gap-1">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.end}
            className={({ isActive }) =>
              `rounded-xl px-4 py-2 font-medium transition-colors ${
                isActive
                  ? 'bg-salmon text-white'
                  : 'text-neutral-700 hover:bg-salmon-light/60'
              }`
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
      <div className="mt-auto px-4 pt-4 text-xs text-neutral-500" title={`Build ${__APP_BUILD__}`}>
        {versaoCurta}
      </div>
    </aside>
  )
}
