/** Histórico, grupos e anexos do chat (`/api/v1/chat`, #23 e #33). */
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from '@tanstack/react-query'
import { chaves } from '@/lib/query'
import {
  apagarConversa,
  apagarGrupo,
  apagarHistoricoChat,
  criarGrupo,
  editarConversa,
  editarGrupo,
  listarConversas,
  listarGrupos,
  listarMensagens,
} from '@/services/chat'

/** A lista de conversas, de 50 em 50. `busca` é feita no servidor (título e mensagens). */
export function useConversas(busca = '') {
  return useInfiniteQuery({
    queryKey: chaves.chat.conversas(busca),
    queryFn: ({ pageParam }) => listarConversas({ busca, pagina: pageParam }),
    initialPageParam: 1,
    getNextPageParam: (ultima) =>
      ultima.pagina < ultima.total_paginas ? ultima.pagina + 1 : undefined,
  })
}

export function useGrupos() {
  return useQuery({ queryKey: chaves.chat.grupos(), queryFn: listarGrupos })
}

export function useMensagens(conversaId: number | null) {
  return useQuery({
    queryKey: chaves.chat.mensagens(conversaId ?? 0),
    queryFn: () => listarMensagens(conversaId as number),
    enabled: conversaId !== null,
  })
}

/**
 * Busca de novo o que uma resposta do tutor mexeu: a conversa (título e posição
 * na lista) e as mensagens dela. Espera terminar, para a tela trocar a mensagem
 * local pela da API sem piscar.
 */
export async function atualizarDepoisDaResposta(queryClient: QueryClient, conversaId: number) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: chaves.chat.todasConversas }),
    queryClient.invalidateQueries({ queryKey: chaves.chat.grupos() }),
    queryClient.fetchQuery({
      queryKey: chaves.chat.mensagens(conversaId),
      queryFn: () => listarMensagens(conversaId),
      staleTime: 0,
    }),
  ])
}

function useInvalidarChat() {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: chaves.chat.todas })
}

export function useRenomearConversa() {
  const invalidar = useInvalidarChat()
  return useMutation({
    mutationFn: ({ id, titulo }: { id: number; titulo: string }) => editarConversa(id, { titulo }),
    onSuccess: invalidar,
  })
}

export function useApagarConversa() {
  const queryClient = useQueryClient()
  const invalidar = useInvalidarChat()
  return useMutation({
    mutationFn: apagarConversa,
    onSuccess: (_, id) => {
      queryClient.removeQueries({ queryKey: chaves.chat.mensagens(id) })
      return invalidar()
    },
  })
}

export function useCriarGrupo() {
  const invalidar = useInvalidarChat()
  return useMutation({
    mutationFn: ({ nome, conversaIds }: { nome: string; conversaIds: number[] }) =>
      criarGrupo(nome, conversaIds),
    onSuccess: invalidar,
  })
}

export function useEditarGrupo() {
  const invalidar = useInvalidarChat()
  return useMutation({
    mutationFn: ({
      id,
      nome,
      conversaIds,
    }: {
      id: number
      nome?: string
      conversaIds?: number[]
    }) => editarGrupo(id, { nome, conversa_ids: conversaIds }),
    onSuccess: invalidar,
  })
}

export function useApagarGrupo() {
  const invalidar = useInvalidarChat()
  return useMutation({ mutationFn: apagarGrupo, onSuccess: invalidar })
}

export function useApagarHistorico() {
  const invalidar = useInvalidarChat()
  return useMutation({ mutationFn: apagarHistoricoChat, onSuccess: invalidar })
}
