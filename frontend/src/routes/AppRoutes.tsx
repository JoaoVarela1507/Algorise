import { Routes, Route } from 'react-router-dom'
import { AppLayout } from '@/layouts/AppLayout'
import { AuthLayout } from '@/layouts/AuthLayout'
import { OnboardingPage } from '@/pages/Onboarding/OnboardingPage'
import { LoginPage } from '@/pages/Auth/LoginPage'
import { CadastroPage } from '@/pages/Auth/CadastroPage'
import { HomePage } from '@/pages/Home/HomePage'
import { TrilhasPage } from '@/pages/Trilhas/TrilhasPage'
import { QuestaoPage } from '@/pages/Questao/QuestaoPage'
import { ChatPage } from '@/pages/Chat/ChatPage'
import { PerfilPage } from '@/pages/Perfil/PerfilPage'
import { CertificadosPage } from '@/pages/Certificados/CertificadosPage'
import { DesignSystemPage } from '@/pages/DesignSystem/DesignSystemPage'

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AuthLayout />}>
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/cadastro" element={<CadastroPage />} />
      </Route>

      <Route element={<AppLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/trilhas" element={<TrilhasPage />} />
        <Route path="/trilhas/:trilhaId/questao/:questaoId" element={<QuestaoPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/perfil" element={<PerfilPage />} />
        <Route path="/certificados" element={<CertificadosPage />} />
        <Route path="/design-system" element={<DesignSystemPage />} />
        <Route path="/design-system" element={<DesignSystemPage />} />
      </Route>
    </Routes>
  )
}
