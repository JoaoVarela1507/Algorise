import { Outlet } from 'react-router-dom'
import { Sidebar } from '@/components/layout/Sidebar'
import { useGamificacaoAoVivo } from '@/hooks/useNotificacoes'

export function AppLayout() {
  // XP, notificações e ranking ao vivo (#37), em qualquer tela logada.
  useGamificacaoAoVivo()
  // Só o conteúdo rola; a sidebar fica sempre com a altura da tela.
  //
  // `relative` no <main>: sem ele, o que é `absolute` lá dentro (os `sr-only`
  // do terminal, por exemplo) se posiciona pela página, e não pelo <main>. Lá
  // embaixo do conteúdo, isso deixava a página mais alta que a tela, e o foco
  // num campo rolava a página inteira, sumindo com o topo da sidebar.
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <main className="relative flex-1 overflow-y-auto p-6">
        <Outlet />
      </main>
    </div>
  )
}
