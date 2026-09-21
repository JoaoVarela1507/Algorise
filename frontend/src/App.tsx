import { BrowserRouter } from 'react-router-dom'
import { AccessibilityProvider } from '@/contexts/AccessibilityContext'
import { AuthProvider } from '@/contexts/AuthContext'
import { AppRoutes } from '@/routes/AppRoutes'
import { Toaster } from '@/components/ui/toaster'

function App() {
  return (
    <BrowserRouter>
      <AccessibilityProvider>
        <AuthProvider>
          <AppRoutes />
          <Toaster />
        </AuthProvider>
      </AccessibilityProvider>
    </BrowserRouter>
  )
}

export default App
