/** Hooks do ranking e do perfil (telas 16, 17 e 18). */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { chaves } from '@/lib/query'
import { atualizarPerfil } from '@/services/auth'
import { buscarRanking, paraLinha, paraLista, type FiltrosRanking } from '@/services/ranking'
import type { AtualizacaoPerfil } from '@/types/usuario'

export function useRanking(filtros: FiltrosRanking = {}) {
  return useQuery({
    queryKey: chaves.ranking.pagina(filtros as Record<string, unknown>),
    queryFn: () => buscarRanking(filtros),
    select: (ranking) => ({
      linhas: paraLista(ranking),
      podio: ranking.podio.map(paraLinha),
      // Onde o aluno está, mesmo quando a posição dele cai fora desta página.
      usuario: ranking.usuario ? paraLinha(ranking.usuario) : null,
      total: ranking.total,
    }),
    placeholderData: (anterior) => anterior,
  })
}

export function useAtualizarPerfil() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (dados: AtualizacaoPerfil) => atualizarPerfil(dados),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: chaves.perfil.todas })
      // Período e nível alimentam a recomendação: mudá-los muda a lista.
      void queryClient.invalidateQueries({ queryKey: chaves.trilhas.recomendadas() })
    },
  })
}
