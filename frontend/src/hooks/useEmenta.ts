/**
 * Hooks da ementa e da trilha guiada (#38).
 *
 * A leitura roda no servidor, sem aviso para o cliente: enquanto ela não
 * termina, `useEmentaAtual` pergunta de novo a cada poucos segundos.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { chaves } from '@/lib/query'
import {
  buscarAssuntos,
  buscarEmentaAtual,
  buscarTrilhaGuiada,
  confirmarEmenta,
  emLeitura,
  relerAssuntos,
  revisarAssuntos,
  type DisciplinaRevisada,
} from '@/services/ementa'
import type { EmentaStatus } from '@/services/onboarding'

/** Ler um PDF e chamar a IA leva segundos, não milissegundos. */
const INTERVALO_DA_LEITURA = 3000

export function useEmentaAtual() {
  return useQuery({
    queryKey: chaves.ementa.atual(),
    queryFn: buscarEmentaAtual,
    refetchInterval: (query) =>
      query.state.data && emLeitura(query.state.data) ? INTERVALO_DA_LEITURA : false,
  })
}

export function useAssuntos(ementa: EmentaStatus | undefined) {
  return useQuery({
    queryKey: chaves.ementa.assuntos(ementa?.id ?? 0),
    queryFn: () => buscarAssuntos(ementa?.id as number),
    // Antes de `prontos` a lista vem vazia: não há o que mostrar.
    enabled: ementa?.status_assuntos === 'prontos',
  })
}

export function useRevisarAssuntos(ementaId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (disciplinas: DisciplinaRevisada[]) => revisarAssuntos(ementaId, disciplinas),
    onSuccess: (assuntos) => {
      queryClient.setQueryData(chaves.ementa.assuntos(ementaId), assuntos)
      // A trilha guiada sai dos assuntos: se já foi gerada, mudou.
      void queryClient.invalidateQueries({ queryKey: chaves.trilhas.guiada() })
    },
  })
}

export function useRelerAssuntos(ementaId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => relerAssuntos(ementaId),
    // Volta para `pendente`, e o intervalo de `useEmentaAtual` retoma sozinho.
    onSuccess: (ementa) => queryClient.setQueryData(chaves.ementa.atual(), ementa),
  })
}

export function useConfirmarEmenta(ementaId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => confirmarEmenta(ementaId),
    onSuccess: (ementa) => {
      queryClient.setQueryData(chaves.ementa.atual(), ementa)
      void queryClient.invalidateQueries({ queryKey: chaves.trilhas.guiada() })
    },
  })
}

export function useTrilhaGuiada() {
  return useQuery({
    queryKey: chaves.trilhas.guiada(),
    queryFn: buscarTrilhaGuiada,
  })
}
