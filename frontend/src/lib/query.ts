import { QueryClient } from '@tanstack/react-query'
import { ApiError } from '@/services/api'

/**
 * Configuração do cache de dados do servidor.
 *
 * O TanStack Query entra **em cima** da `services/api.ts`, que continua
 * cuidando do token e da renovação no 401. O que ele acrescenta é o que não dá
 * para fazer bem na mão: uma requisição só quando duas telas pedem o mesmo
 * dado, revalidação em segundo plano e invalidação depois de uma mutation.
 */

/** Meio minuto: o catálogo não muda a cada segundo, e o aluno troca de aba direto. */
const TEMPO_FRESCO = 30_000

/** Quantas vezes insistir num erro que pode ser de rede. */
const TENTATIVAS = 2

export function deveTentarDeNovo(tentativa: number, erro: unknown): boolean {
  // Erro do cliente (404, 403, 422) não melhora tentando de novo — e um 403 de
  // passo bloqueado repetido quatro vezes só atrasa a tela de erro.
  if (erro instanceof ApiError && erro.status >= 400 && erro.status < 500) {
    return false
  }
  return tentativa < TENTATIVAS
}

export function criarQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: TEMPO_FRESCO,
        retry: deveTentarDeNovo,
        // Revalidar ao voltar para a aba é bom para ranking e progresso, que
        // mudam por fora; refazer tudo a cada foco de janela, não.
        refetchOnWindowFocus: true,
        refetchOnReconnect: true,
      },
      mutations: {
        // Mutation que falhou é ação do aluno: ele decide se tenta de novo.
        retry: false,
      },
    },
  })
}

/**
 * Chaves de cache num lugar só.
 *
 * Invalidação depende de a chave bater exatamente; com string solta espalhada
 * pelos hooks, um `['trilhas']` aqui e um `['trilha']` ali passam despercebidos
 * e a tela para de atualizar sem ninguém entender por quê.
 */
export const chaves = {
  trilhas: {
    todas: ['trilhas'] as const,
    catalogo: (filtros: Record<string, unknown>) => ['trilhas', 'catalogo', filtros] as const,
    recomendadas: () => ['trilhas', 'recomendadas'] as const,
    detalhe: (slug: string) => ['trilhas', 'detalhe', slug] as const,
    passo: (slug: string, ordem: number) => ['trilhas', 'passo', slug, ordem] as const,
  },
  ranking: {
    todas: ['ranking'] as const,
    pagina: (filtros: Record<string, unknown>) => ['ranking', filtros] as const,
  },
  perfil: {
    todas: ['perfil'] as const,
    meu: () => ['perfil', 'me'] as const,
  },
} as const
