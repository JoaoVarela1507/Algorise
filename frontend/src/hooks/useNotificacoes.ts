/** Centro de notificações e os eventos de gamificação ao vivo (#37). */
import { useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query'
import { toast } from '@/components/ui/toaster'
import { aplicarMudancas } from '@/lib/rankingAoVivo'
import { chaves } from '@/lib/query'
import type { PainelApi } from '@/services/gamificacao'
import {
  contarNaoLidas,
  listarNotificacoes,
  marcarLida,
  marcarTodasLidas,
  TIPOS_DE_NOTIFICACAO,
} from '@/services/notificacoes'
import type { EntradaRankingApi, FiltrosRanking, RankingApi } from '@/services/ranking'
import type { Evento } from '@/services/tempoReal'
import { useAuthStore } from '@/stores/useAuthStore'
import { useCanal } from '@/stores/useTempoRealStore'

export function useNotificacoes(habilitado = true) {
  return useQuery({
    queryKey: chaves.notificacoes.lista(),
    queryFn: () => listarNotificacoes(),
    enabled: habilitado,
  })
}

export function useNaoLidas() {
  const logado = useAuthStore((estado) => estado.usuario !== null)
  return useQuery({
    queryKey: chaves.notificacoes.contagem(),
    queryFn: contarNaoLidas,
    enabled: logado,
  })
}

export function useMarcarLida() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: marcarLida,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: chaves.notificacoes.todas }),
  })
}

export function useMarcarTodasLidas() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: marcarTodasLidas,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: chaves.notificacoes.todas }),
  })
}

/**
 * Liga os canais de tempo real da gamificação. O `AppLayout` chama uma vez.
 *
 * - `notificacoes:{id}`: o `xp.ganho` atualiza o painel em cache (o contador e a
 *   barra se mexem, sem animação se o aluno pediu menos movimento), e as
 *   notificações aparecem num toast e no sino;
 * - `ranking:geral`: o `ranking.atualizado` entra direto nos rankings em cache.
 */
export function useGamificacaoAoVivo() {
  const queryClient = useQueryClient()
  const usuarioId = useAuthStore((estado) => estado.usuario?.id ?? null)

  useCanal(usuarioId ? `notificacoes:${usuarioId}` : null, (evento) =>
    tratarNotificacao(queryClient, evento),
  )
  useCanal(usuarioId ? 'ranking:geral' : null, (evento) => {
    if (evento.evento === 'ranking.atualizado') aplicarNoCache(queryClient, evento)
  })
}

export function tratarNotificacao(queryClient: QueryClient, evento: Evento) {
  const payload = evento.payload ?? {}
  if (evento.evento === 'xp.ganho') {
    queryClient.setQueryData<PainelApi>(chaves.gamificacao.painel(), (painel) =>
      painel
        ? {
            ...painel,
            xp_total: Number(payload.xp_total),
            nivel: Number(payload.nivel),
            xp_no_nivel: Number(payload.xp_no_nivel),
            xp_para_o_proximo: Number(payload.xp_para_o_proximo),
          }
        : painel,
    )
    toast(`+${Number(payload.valor)} XP`)
    return
  }
  if ((TIPOS_DE_NOTIFICACAO as readonly string[]).includes(evento.evento)) {
    void queryClient.invalidateQueries({ queryKey: chaves.notificacoes.todas })
    toast(String(payload.titulo ?? ''), { description: String(payload.mensagem ?? '') })
  }
}

export function aplicarNoCache(queryClient: QueryClient, evento: Evento) {
  const payload = evento.payload ?? {}
  const mudancas = (payload.mudancas ?? []) as EntradaRankingApi[]
  const total = Number(payload.total ?? 0)
  for (const [chave, ranking] of queryClient.getQueriesData<RankingApi>({
    queryKey: chaves.ranking.todas,
  })) {
    if (!ranking) continue
    const filtros = (chave[1] ?? {}) as FiltrosRanking
    queryClient.setQueryData(chave, aplicarMudancas(ranking, mudancas, total, filtros))
  }
}
