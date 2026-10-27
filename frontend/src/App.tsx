import { useState, type ReactNode } from 'react'
import { BrowserRouter } from 'react-router-dom'
import { MotionConfig } from 'framer-motion'
import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { criarQueryClient } from '@/lib/query'
import { AccessibilityProvider, useAccessibility } from '@/contexts/AccessibilityContext'
import { AuthProvider } from '@/contexts/AuthContext'
import { ThemeProvider } from '@/contexts/ThemeContext'
import { AppRoutes } from '@/routes/AppRoutes'
import { Toaster } from '@/components/ui/toaster'

/**
 * Animações do app inteiro: somem quando o sistema pede menos movimento
 * ("user") ou quando o aluno liga "Reduzir animações" nas Configurações.
 */
function ConfiguracaoAnimacoes({ children }: { children: ReactNode }) {
  const { reduzirAnimacoes } = useAccessibility()
  return (
    <MotionConfig reducedMotion={reduzirAnimacoes ? 'always' : 'user'}>{children}</MotionConfig>
  )
}

function App() {
  // Em estado, e não em módulo: assim cada montagem do app (os testes montam
  // várias) começa com o cache limpo, em vez de herdar o do teste anterior.
  const [queryClient] = useState(criarQueryClient)

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ThemeProvider>
          <AccessibilityProvider>
            <ConfiguracaoAnimacoes>
              <AuthProvider>
                <AppRoutes />
                <Toaster />
              </AuthProvider>
            </ConfiguracaoAnimacoes>
          </AccessibilityProvider>
        </ThemeProvider>
      </BrowserRouter>
      {/* Só no `npm run dev`: o Vite remove isto do build de produção. */}
      {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  )
}

export default App
