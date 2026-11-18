import { Outlet } from 'react-router-dom'
import { Comemoracoes } from '@/components/gamificacao/Comemoracoes'
import { BarraAbas, BarraTopo } from '@/components/layout/NavegacaoMobile'
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
  //
  // No celular a sidebar dá lugar à barra do topo e às abas embaixo; o
  // `pb-24` do <main> deixa o fim do conteúdo acima das abas.
  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-background md:flex-row">
      <BarraTopo />
      <Sidebar />
      <main className="relative min-w-0 flex-1 overflow-y-auto p-4 pb-24 md:p-6">
        <Outlet />
      </main>
      <BarraAbas />
      <Comemoracoes />
    </div>
  )
}
