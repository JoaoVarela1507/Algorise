import type { ReactNode } from 'react'
import { BrowserRouter } from 'react-router-dom'
import { MotionConfig } from 'framer-motion'
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
  return (
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
  )
}

export default App
