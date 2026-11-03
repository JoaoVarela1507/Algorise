/** Hooks de XP, nível e streak (telas 16 e 20). */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { chaves } from '@/lib/query'
import {
  buscarConquistas,
  buscarMetaDiaria,
  buscarPainel,
  paraMetaDiaria,
  registrarCheckin,
} from '@/services/gamificacao'

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

/** XP, desafios e minutos de hoje, para o anel de meta da home. */
export function useMetaDiaria() {
  return useQuery({
    queryKey: chaves.gamificacao.metaDiaria(),
    queryFn: buscarMetaDiaria,
    select: paraMetaDiaria,
  })
}

export function useConquistas() {
  return useQuery({
    queryKey: chaves.gamificacao.conquistas(),
    queryFn: buscarConquistas,
  })
}
