import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { ehLoginTeste, loginTesteHabilitado, USUARIO_TESTE } from '@/lib/loginTeste'
import { configurarAutenticacao } from '@/services/api'
import * as auth from '@/services/auth'
import type { AtualizacaoPerfil, Usuario } from '@/types/usuario'

interface AuthContextValue {
  usuario: Usuario | null
  /** `true` enquanto a sessão guardada é restaurada, ao abrir o app. */
  carregando: boolean
  entrar: (email: string, senha: string, manterConectado: boolean) => Promise<void>
  cadastrar: (dados: { username: string; email: string; senha: string }) => Promise<void>
  /** Fim do login social, chamado pela rota `/auth/callback`. */
  concluirLoginSocial: (tokens: { access_token: string; refresh_token: string }) => Promise<void>
  logout: () => void
  atualizarUsuario: (dados: Partial<Usuario>) => void
  /** Salva nível, trilha, instituição etc. na API (`PATCH /usuarios/eu`). */
  atualizarPerfil: (dados: AtualizacaoPerfil) => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

// Marca que a sessão aberta é a de teste, para ela sobreviver a uma recarga.
const CHAVE_SESSAO_TESTE = 'algorise:sessao-teste'

function sessaoTesteGuardada() {
  return loginTesteHabilitado && sessionStorage.getItem(CHAVE_SESSAO_TESTE) === '1'
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(() =>
    sessaoTesteGuardada() ? USUARIO_TESTE : null,
  )
  const [carregando, setCarregando] = useState(
    () => !sessaoTesteGuardada() && auth.temSessaoGuardada(),
  )

  // A camada de API pede a renovação por aqui num 401. Se ela falhar, a
  // sessão acabou de verdade e o aluno volta para o login.
  useEffect(() => {
    configurarAutenticacao({
      renovar: async () => {
        const renovado = await auth.renovarSessao()
        if (renovado) {
          setUsuario(renovado)
        } else if (!auth.temSessaoGuardada() && !sessaoTesteGuardada()) {
          setUsuario(null)
        }
        return renovado !== null
      },
    })
    return () => configurarAutenticacao(null)
  }, [])

  // Recarregou a página: o access token (em memória) sumiu, o refresh não.
  useEffect(() => {
    if (!carregando) return
    auth
      .renovarSessao()
      .then(setUsuario)
      .finally(() => setCarregando(false))
    // Só na montagem.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const entrar = useCallback(async (email: string, senha: string, manterConectado: boolean) => {
    if (ehLoginTeste(email, senha)) {
      sessionStorage.setItem(CHAVE_SESSAO_TESTE, '1')
      setUsuario(USUARIO_TESTE)
      return
    }
    sessionStorage.removeItem(CHAVE_SESSAO_TESTE)
    setUsuario(await auth.entrar(email, senha, manterConectado))
  }, [])

  const cadastrar = useCallback(
    async (dados: { username: string; email: string; senha: string }) => {
      sessionStorage.removeItem(CHAVE_SESSAO_TESTE)
      setUsuario(await auth.cadastrar(dados))
    },
    [],
  )

  const concluirLoginSocial = useCallback(
    async (tokens: { access_token: string; refresh_token: string }) => {
      sessionStorage.removeItem(CHAVE_SESSAO_TESTE)
      setUsuario(await auth.concluirLoginSocial(tokens))
    },
    [],
  )

  const logout = useCallback(() => {
    sessionStorage.removeItem(CHAVE_SESSAO_TESTE)
    setUsuario(null)
    void auth.sair()
  }, [])

  const atualizarUsuario = useCallback((dados: Partial<Usuario>) => {
    setUsuario((atual) => {
      if (!atual) return atual
      const novo = { ...atual, ...dados }
      auth.guardarPerfilLocal(novo)
      return novo
    })
  }, [])

  const atualizarPerfil = useCallback(
    async (dados: AtualizacaoPerfil) => {
      // O login de teste não tem token: o perfil fica só neste navegador.
      if (sessaoTesteGuardada()) {
        atualizarUsuario(dados)
        return
      }
      setUsuario(await auth.atualizarPerfil(dados))
    },
    [atualizarUsuario],
  )

  return (
    <AuthContext.Provider
      value={{
        usuario,
        carregando,
        entrar,
        cadastrar,
        concluirLoginSocial,
        logout,
        atualizarUsuario,
        atualizarPerfil,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth deve ser usado dentro de um AuthProvider')
  }
  return context
}
