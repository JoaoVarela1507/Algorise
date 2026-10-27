import { useEffect, useState, type ReactNode } from 'react'
import { BrowserRouter } from 'react-router-dom'
import { MotionConfig } from 'framer-motion'
import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { criarQueryClient } from '@/lib/query'
import { AppRoutes } from '@/routes/AppRoutes'
import { PreferenciasDaConta } from '@/components/configuracoes/PreferenciasDaConta'
import { Toaster } from '@/components/ui/toaster'
import { useAccessibilityStore } from '@/stores/useAccessibilityStore'
import { ligarSessao } from '@/stores/useAuthStore'
// Aplica o tema no <html> já ao carregar, antes de qualquer tela pedir.
import '@/stores/useThemeStore'

/**
 * Animações do app inteiro: somem quando o sistema pede menos movimento
 * ("user") ou quando o aluno liga "Reduzir animações" nas Configurações.
 */
function ConfiguracaoAnimacoes({ children }: { children: ReactNode }) {
  const reduzirAnimacoes = useAccessibilityStore((estado) => estado.reduzirAnimacoes)
  return (
    <MotionConfig reducedMotion={reduzirAnimacoes ? 'always' : 'user'}>{children}</MotionConfig>
  )
}

function App() {
  // Em estado, e não em módulo: assim cada montagem do app (os testes montam
  // várias) começa com o cache limpo, em vez de herdar o do teste anterior.
  const [queryClient] = useState(criarQueryClient)

  useEffect(() => ligarSessao(queryClient), [queryClient])

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ConfiguracaoAnimacoes>
          <PreferenciasDaConta />
          <AppRoutes />
          <Toaster />
        </ConfiguracaoAnimacoes>
      </BrowserRouter>
      {/* Só no `npm run dev`: o Vite remove isto do build de produção. */}
      {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  )
}

export default App
