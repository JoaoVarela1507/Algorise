import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/stores/useAuthStore'

export function RequireAuth() {
  const usuario = useAuthStore((estado) => estado.usuario)
  const carregando = useAuthStore((estado) => estado.carregando)

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
