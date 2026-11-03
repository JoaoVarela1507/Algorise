import { Outlet } from 'react-router-dom'
import { Sidebar } from '@/components/layout/Sidebar'
import { useGamificacaoAoVivo } from '@/hooks/useNotificacoes'

export function AppLayout() {
  // XP, notificações e ranking ao vivo (#37), em qualquer tela logada.
  useGamificacaoAoVivo()
  // Só o conteúdo rola; a sidebar fica sempre com a altura da tela.
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-6">
        <Outlet />
      </main>
    </div>
  )
}
