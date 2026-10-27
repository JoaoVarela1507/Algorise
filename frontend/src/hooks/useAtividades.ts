/**
 * Hooks das atividades.
 *
 * Quem decide se o aluno acertou é o servidor (#30): o terminal simulado
 * encena a saída, mas o acerto que vale XP vem daqui.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { chaves } from '@/lib/query'
import {
  buscarTentativas,
  concluirPasso,
  submeterResposta,
  type RespostaDoAluno,
} from '@/services/atividades'

export function useTentativas(atividadeId: number | undefined) {
  return useQuery({
    queryKey: chaves.atividades.tentativas(atividadeId ?? 0),
    queryFn: () => buscarTentativas(atividadeId as number),
    enabled: Number.isInteger(atividadeId),
  })
}

export function useSubmeterResposta(atividadeId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (resposta: RespostaDoAluno) => submeterResposta(atividadeId, resposta),
    onSuccess: (correcao) => {
      void queryClient.invalidateQueries({
        queryKey: chaves.atividades.tentativas(atividadeId),
      })
      // XP mudou: perfil e ranking saem do lugar.
      if (correcao.xp_ganho > 0) {
        void queryClient.invalidateQueries({ queryKey: chaves.perfil.todas })
        void queryClient.invalidateQueries({ queryKey: chaves.ranking.todas })
        void queryClient.invalidateQueries({ queryKey: chaves.gamificacao.todas })
      }
    },
  })
}

export function useConcluirPasso(slug: string | undefined) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (ordem: number) => concluirPasso(slug as string, ordem),
    onSuccess: () => {
      // O passo fechado muda progresso, catálogo, detalhe e ranking.
      void queryClient.invalidateQueries({ queryKey: chaves.trilhas.todas })
      void queryClient.invalidateQueries({ queryKey: chaves.perfil.todas })
      void queryClient.invalidateQueries({ queryKey: chaves.ranking.todas })
      void queryClient.invalidateQueries({ queryKey: chaves.gamificacao.todas })
    },
  })
}
