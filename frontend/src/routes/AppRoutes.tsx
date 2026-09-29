import { Routes, Route } from 'react-router-dom'
import { AppLayout } from '@/layouts/AppLayout'
import { AuthLayout } from '@/layouts/AuthLayout'
import { BoasVindasPage } from '@/pages/Auth/BoasVindasPage'
import { OnboardingPage } from '@/pages/Onboarding/OnboardingPage'
import { LoginPage } from '@/pages/Auth/LoginPage'
import { CadastroPage } from '@/pages/Auth/CadastroPage'
import { EsqueciSenhaPage } from '@/pages/Auth/EsqueciSenhaPage'
import { OAuthCallbackPage } from '@/pages/Auth/OAuthCallbackPage'
import { RedefinirSenhaPage } from '@/pages/Auth/RedefinirSenhaPage'
import { HomePage } from '@/pages/Home/HomePage'
import { TrilhasPage } from '@/pages/Trilhas/TrilhasPage'
import { QuestaoPage } from '@/pages/Questao/QuestaoPage'
import { ChatPage } from '@/pages/Chat/ChatPage'
import { PerfilPage } from '@/pages/Perfil/PerfilPage'
import { CertificadosPage } from '@/pages/Certificados/CertificadosPage'
import { ConfiguracoesPage } from '@/pages/Configuracoes/ConfiguracoesPage'
import { DesignSystemPage } from '@/pages/DesignSystem/DesignSystemPage'
import { RequireAuth } from '@/routes/RequireAuth'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/boas-vindas" element={<BoasVindasPage />} />

      <Route element={<AuthLayout />}>
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/cadastro" element={<CadastroPage />} />
        <Route path="/esqueci-senha" element={<EsqueciSenhaPage />} />
        <Route path="/redefinir-senha" element={<RedefinirSenhaPage />} />
        <Route path="/auth/callback" element={<OAuthCallbackPage />} />
      </Route>

      <Route element={<RequireAuth />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/trilhas" element={<TrilhasPage />} />
          <Route path="/trilhas/:trilhaId/questao/:questaoId" element={<QuestaoPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/perfil" element={<PerfilPage />} />
          <Route path="/configuracoes" element={<ConfiguracoesPage />} />
          <Route path="/certificados" element={<CertificadosPage />} />
          <Route path="/design-system" element={<DesignSystemPage />} />
        </Route>
      </Route>
    </Routes>
  )
}
