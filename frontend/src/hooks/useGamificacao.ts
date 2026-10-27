/** Hooks de XP, nível e streak (telas 16 e 20). */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { chaves } from '@/lib/query'
import { buscarPainel, registrarCheckin } from '@/services/gamificacao'

export function usePainel(habilitado = true) {
  return useQuery({
    queryKey: chaves.gamificacao.painel(),
    queryFn: buscarPainel,
    enabled: habilitado,
  })
}

export function useCheckin() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: registrarCheckin,
    // A resposta já é o painel atualizado: usar direto evita uma ida a mais.
    onSuccess: (painel) => queryClient.setQueryData(chaves.gamificacao.painel(), painel),
  })
}
