import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'

export function RequireAuth() {
  const { usuario, carregando } = useAuth()

  // Ao recarregar, a sessão guardada ainda está sendo restaurada: mandar para
  // o login agora expulsaria um aluno que está logado.
  if (carregando) {
    return null
  }

  if (!usuario) {
    return <Navigate to="/boas-vindas" replace />
  }

  return <Outlet />
}
