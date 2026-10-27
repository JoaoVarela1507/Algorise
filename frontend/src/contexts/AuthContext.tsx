import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from '@/components/ui/toaster'
import { ehLoginTeste, loginTesteHabilitado, USUARIO_TESTE } from '@/lib/loginTeste'
import { chaves } from '@/lib/query'
import { configurarAutenticacao } from '@/services/api'
import * as auth from '@/services/auth'
import type { AtualizacaoPerfil, Preferencias, TipoTrilha, Usuario } from '@/types/usuario'

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
  /** Salva nível, trilha, instituição etc. na API (`PATCH /usuarios/me`). */
  atualizarPerfil: (dados: AtualizacaoPerfil) => Promise<void>
  /** Guiada, Livre ou Mista (`PATCH /usuarios/me/trilha`). Recarrega as trilhas. */
  trocarModoTrilha: (modo: TipoTrilha) => Promise<void>
  /** Leva as preferências de acessibilidade para a conta. */
  salvarPreferencias: (dados: Partial<Preferencias>) => Promise<void>
  enviarAvatar: (arquivo: File) => Promise<void>
  removerAvatar: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

// Marca que a sessão aberta é a de teste, para ela sobreviver a uma recarga.
const CHAVE_SESSAO_TESTE = 'algorise:sessao-teste'

function sessaoTesteGuardada() {
  return loginTesteHabilitado && sessionStorage.getItem(CHAVE_SESSAO_TESTE) === '1'
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
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
    const { usuario: logado, aviso } = await auth.entrar(email, senha, manterConectado)
    setUsuario(logado)
    if (aviso) toast(aviso)
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

  const trocarModoTrilha = useCallback(
    async (modo: TipoTrilha) => {
      if (sessaoTesteGuardada()) {
        atualizarUsuario({ tipoTrilha: modo })
      } else {
        setUsuario(await auth.trocarModoTrilha(modo))
      }
      // Cada modo libera passos diferentes: o cadeado em cache estaria errado.
      void queryClient.invalidateQueries({ queryKey: chaves.trilhas.todas })
    },
    [atualizarUsuario, queryClient],
  )

  const salvarPreferencias = useCallback(async (dados: Partial<Preferencias>) => {
    // Sem conta de verdade, o navegador já guardou: não há para onde levar.
    if (sessaoTesteGuardada()) return
    const preferencias = await auth.salvarPreferencias(dados)
    setUsuario((atual) => (atual ? { ...atual, preferencias } : atual))
  }, [])

  const enviarAvatar = useCallback(async (arquivo: File) => {
    if (sessaoTesteGuardada()) {
      throw new Error('A foto do perfil não está disponível no login de teste.')
    }
    setUsuario(await auth.enviarAvatar(arquivo))
  }, [])

  const removerAvatar = useCallback(async () => {
    if (sessaoTesteGuardada()) return
    setUsuario(await auth.removerAvatar())
  }, [])

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
        trocarModoTrilha,
        salvarPreferencias,
        enviarAvatar,
        removerAvatar,
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
