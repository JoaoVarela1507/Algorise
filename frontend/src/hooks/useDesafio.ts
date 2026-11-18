/**
 * Hooks do desafio de código (#25).
 *
 * O código roda no servidor, numa sandbox, e demora um pouco: `POST` devolve só
 * o id da execução, e a tela pergunta pelo resultado até ele sair da fila. Quem
 * diz se passou é o servidor, que também paga o XP.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { chaves } from '@/lib/query'
import {
  buscarDesafio,
  buscarExecucao,
  emAndamento,
  executarDesafio,
  type ExecucaoApi,
} from '@/services/desafios'

/** Intervalo entre as perguntas: cada caso leva menos de um segundo no modo leve. */
const INTERVALO_DA_EXECUCAO = 700

export function useDesafio(id: number | undefined) {
  return useQuery({
    queryKey: chaves.desafios.detalhe(id ?? 0),
    queryFn: () => buscarDesafio(id as number),
    enabled: Number.isInteger(id),
    staleTime: Infinity,
  })
}

/** Envia o código e acompanha a execução até o veredito. */
export function useVerificarDesafio(id: number) {
  const queryClient = useQueryClient()
  const [execucaoId, setExecucaoId] = useState<string | null>(null)

  const envio = useMutation({
    mutationFn: (codigo: string) => executarDesafio(id, codigo),
    onSuccess: (naFila) => setExecucaoId(naFila.id),
  })

  const execucao = useQuery({
    queryKey: chaves.desafios.execucao(execucaoId ?? ''),
    queryFn: async () => {
      const resultado = await buscarExecucao(execucaoId as string)
      if (resultado.aprovada) atualizarDepoisDoAcerto()
      return resultado
    },
    enabled: Boolean(execucaoId),
    refetchInterval: (query) =>
      emAndamento(query.state.data) || !query.state.data ? INTERVALO_DA_EXECUCAO : false,
  })

  function atualizarDepoisDoAcerto() {
    // O desafio aprovado vira atividade feita (o ✓ na trilha) e paga XP.
    void queryClient.invalidateQueries({ queryKey: chaves.trilhas.todas })
    void queryClient.invalidateQueries({ queryKey: chaves.perfil.todas })
    void queryClient.invalidateQueries({ queryKey: chaves.ranking.todas })
    void queryClient.invalidateQueries({ queryKey: chaves.gamificacao.todas })
  }

  const resultado: ExecucaoApi | undefined = execucao.data
  const rodando = envio.isPending || (Boolean(execucaoId) && (!resultado || emAndamento(resultado)))

  return {
    verificar: (codigo: string) => {
      setExecucaoId(null)
      envio.mutate(codigo)
    },
    /** Some com o resultado e volta ao editor ("Voltar para Desafio"). */
    limpar: () => setExecucaoId(null),
    rodando,
    resultado: resultado && !emAndamento(resultado) ? resultado : null,
    erroDoEnvio: envio.error,
  }
}
