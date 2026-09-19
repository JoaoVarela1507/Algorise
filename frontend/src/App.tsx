import { BrowserRouter } from 'react-router-dom'
import { AccessibilityProvider } from '@/contexts/AccessibilityContext'
import { AuthProvider } from '@/contexts/AuthContext'
import { AppRoutes } from '@/routes/AppRoutes'

function App() {
  return (
    <BrowserRouter>
      <AccessibilityProvider>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </AccessibilityProvider>
    </BrowserRouter>
  )
}

export default App
