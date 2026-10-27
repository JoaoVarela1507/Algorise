import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type { QueryClient } from '@tanstack/react-query'
import { toast } from '@/components/ui/toaster'
import { ehLoginTeste, loginTesteHabilitado, USUARIO_TESTE } from '@/lib/loginTeste'
import { chaves } from '@/lib/query'
import { configurarAutenticacao } from '@/services/api'
import * as auth from '@/services/auth'
import * as onboarding from '@/services/onboarding'
import { useOnboardingStore } from '@/stores/useOnboardingStore'
import type { AtualizacaoPerfil, Preferencias, TipoTrilha, Usuario } from '@/types/usuario'

interface AuthState {
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
  /** Fim do onboarding (`POST /onboarding`): nível, trilha e dados acadêmicos. */
  concluirOnboarding: (dados: onboarding.DadosOnboarding) => Promise<void>
}

// Marca que a sessão aberta é a de teste, para ela sobreviver a uma recarga.
const CHAVE_SESSAO_TESTE = 'algorise:sessao-teste'

function sessaoTesteGuardada() {
  return loginTesteHabilitado && sessionStorage.getItem(CHAVE_SESSAO_TESTE) === '1'
}

// O cache do React Query, para recarregar as trilhas quando o perfil muda.
// Chega pelo `ligarSessao`, porque o store vive fora da árvore do React.
let queryClient: QueryClient | null = null

function invalidarTrilhas() {
  void queryClient?.invalidateQueries({ queryKey: chaves.trilhas.todas })
}

/**
 * Sessão do aluno (telas 5 e 6). Não é persistida aqui: o refresh token já
 * fica guardado pelo `services/auth` (no `localStorage` com "manter-se
 * conectado", no `sessionStorage` sem), e o access token só em memória.
 * Recarregar a página restaura a sessão a partir dele; ver `ligarSessao`.
 */
export const useAuthStore = create<AuthState>()(
  devtools(
    (set, get) => {
      /** Troca o aluno da sessão, e com ele o dono do rascunho de onboarding. */
      function trocarAluno(usuario: Usuario | null) {
        set({ usuario })
        useOnboardingStore.getState().vincularAluno(usuario?.id ?? null)
      }

      return {
        usuario: sessaoTesteGuardada() ? USUARIO_TESTE : null,
        carregando: !sessaoTesteGuardada() && auth.temSessaoGuardada(),

        entrar: async (email, senha, manterConectado) => {
          if (ehLoginTeste(email, senha)) {
            sessionStorage.setItem(CHAVE_SESSAO_TESTE, '1')
            trocarAluno(USUARIO_TESTE)
            return
          }
          sessionStorage.removeItem(CHAVE_SESSAO_TESTE)
          const { usuario, aviso } = await auth.entrar(email, senha, manterConectado)
          trocarAluno(usuario)
          if (aviso) toast(aviso)
        },

        cadastrar: async (dados) => {
          sessionStorage.removeItem(CHAVE_SESSAO_TESTE)
          trocarAluno(await auth.cadastrar(dados))
        },

        concluirLoginSocial: async (tokens) => {
          sessionStorage.removeItem(CHAVE_SESSAO_TESTE)
          trocarAluno(await auth.concluirLoginSocial(tokens))
        },

        logout: () => {
          sessionStorage.removeItem(CHAVE_SESSAO_TESTE)
          trocarAluno(null)
          void auth.sair()
        },

        atualizarUsuario: (dados) => {
          const atual = get().usuario
          if (!atual) return
          const novo = { ...atual, ...dados }
          auth.guardarPerfilLocal(novo)
          set({ usuario: novo })
        },

        atualizarPerfil: async (dados) => {
          // O login de teste não tem token: o perfil fica só neste navegador.
          if (sessaoTesteGuardada()) {
            get().atualizarUsuario(dados)
            return
          }
          set({ usuario: await auth.atualizarPerfil(dados) })
        },

        trocarModoTrilha: async (modo) => {
          if (sessaoTesteGuardada()) {
            get().atualizarUsuario({ tipoTrilha: modo })
          } else {
            set({ usuario: await auth.trocarModoTrilha(modo) })
          }
          // Cada modo libera passos diferentes: o cadeado em cache estaria errado.
          invalidarTrilhas()
        },

        salvarPreferencias: async (dados) => {
          // Sem conta de verdade, o navegador já guardou: não há para onde levar.
          if (sessaoTesteGuardada()) return
          const preferencias = await auth.salvarPreferencias(dados)
          const atual = get().usuario
          if (atual) set({ usuario: { ...atual, preferencias } })
        },

        enviarAvatar: async (arquivo) => {
          if (sessaoTesteGuardada()) {
            throw new Error('A foto do perfil não está disponível no login de teste.')
          }
          set({ usuario: await auth.enviarAvatar(arquivo) })
        },

        removerAvatar: async () => {
          if (sessaoTesteGuardada()) return
          set({ usuario: await auth.removerAvatar() })
        },

        concluirOnboarding: async (dados) => {
          if (sessaoTesteGuardada()) {
            get().atualizarUsuario({
              nivelExperiencia: dados.nivelExperiencia,
              tipoTrilha: dados.tipoTrilha,
              instituicao: dados.instituicao.texto.trim() || undefined,
              curso: dados.curso.texto.trim() || undefined,
              periodo: dados.periodo,
              onboardingConcluido: true,
            })
          } else {
            set({ usuario: await onboarding.concluirOnboarding(dados) })
            // Período e modo mudam o que é recomendado e o que está liberado.
            invalidarTrilhas()
          }
          useOnboardingStore.getState().limpar()
        },
      }
    },
    { name: 'auth', enabled: import.meta.env.DEV },
  ),
)

/**
 * Liga o store à camada de API e ao cache do React Query, e restaura a sessão
 * guardada. O `App` chama ao montar; devolve a limpeza.
 */
export function ligarSessao(cliente: QueryClient) {
  queryClient = cliente

  // A camada de API pede a renovação por aqui num 401. Se ela falhar, a
  // sessão acabou de verdade e o aluno volta para o login.
  configurarAutenticacao({
    renovar: async () => {
      const renovado = await auth.renovarSessao()
      if (renovado) {
        useAuthStore.setState({ usuario: renovado })
      } else if (!auth.temSessaoGuardada() && !sessaoTesteGuardada()) {
        useAuthStore.setState({ usuario: null })
        useOnboardingStore.getState().vincularAluno(null)
      }
      return renovado !== null
    },
  })

  // Recarregou a página: o access token (em memória) sumiu, o refresh não.
  // O `renovarSessao` junta chamadas simultâneas, então a montagem dupla do
  // `StrictMode` não gasta o refresh duas vezes.
  if (useAuthStore.getState().carregando) {
    auth
      .renovarSessao()
      .then((usuario) => {
        useAuthStore.setState({ usuario })
        // Sem confirmar a sessão (servidor fora, por exemplo), o rascunho fica.
        if (usuario) useOnboardingStore.getState().vincularAluno(usuario.id)
      })
      .finally(() => useAuthStore.setState({ carregando: false }))
  }

  return () => {
    configurarAutenticacao(null)
    queryClient = null
  }
}
