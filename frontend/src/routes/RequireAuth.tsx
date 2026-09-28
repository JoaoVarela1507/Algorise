import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'

export function RequireAuth() {
  const { usuario } = useAuth()

  if (!usuario) {
    return <Navigate to="/boas-vindas" replace />
  }

  return <Outlet />
}
