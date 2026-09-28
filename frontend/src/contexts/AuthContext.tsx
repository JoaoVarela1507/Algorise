import { createContext, useContext, useState, type ReactNode } from 'react'
import type { Usuario } from '@/types/usuario'

interface AuthContextValue {
  usuario: Usuario | null
  login: (usuario: Usuario) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null)

  function login(usuarioLogado: Usuario) {
    setUsuario(usuarioLogado)
  }

  function logout() {
    setUsuario(null)
  }

  return <AuthContext.Provider value={{ usuario, login, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth deve ser usado dentro de um AuthProvider')
  }
  return context
}
