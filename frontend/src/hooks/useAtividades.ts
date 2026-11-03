/**
 * Hooks das atividades.
 *
 * Quem decide se o aluno acertou é o servidor (#30): o terminal simulado
 * encena a saída, mas o acerto que vale XP vem daqui.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import { chaves } from '@/lib/query'
import {
  buscarExercicios,
  buscarTentativas,
  concluirPasso,
  reportarPasso,
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

export type EstadoCorrecao = 'aguardando' | 'certa' | 'errada' | 'em-analise'

export interface Correcao {
  estado: EstadoCorrecao
  /** Tentativas erradas nesta visita à atividade. */
  tentativas: number
  /** O que o servidor disse da última resposta ("2 de 3 lacunas certas"…). */
  feedback: string | null
  enviando: boolean
  enviar: (conteudo: string) => Promise<void>
}

/**
 * Envia a resposta e guarda o veredito do servidor, igual para todo tipo de
 * atividade: quem diz se acertou é a API (#30), nunca a tela.
 */
export function useCorrecao(atividadeId: number, concluida = false): Correcao {
  const submissao = useSubmeterResposta(atividadeId)
  const [estado, setEstado] = useState<EstadoCorrecao>(concluida ? 'certa' : 'aguardando')
  const [tentativas, setTentativas] = useState(0)
  const [feedback, setFeedback] = useState<string | null>(null)
  // Tempo desde a última tentativa, não desde a abertura: a meta do dia soma
  // as tentativas, e medir do início contaria o mesmo minuto várias vezes.
  const desde = useRef(Date.now())

  async function enviar(conteudo: string) {
    const tempoGastoSegundos = Math.round((Date.now() - desde.current) / 1000)
    try {
      const correcao = await submissao.mutateAsync({ conteudo, tempoGastoSegundos })
      desde.current = Date.now()
      setFeedback(correcao.feedback)
      if (correcao.correta) setEstado('certa')
      else if (correcao.em_analise) setEstado('em-analise')
      else {
        setEstado('errada')
        setTentativas((n) => n + 1)
      }
    } catch {
      // A API não respondeu: não dá para afirmar que errou, então a tentativa
      // não é contada e o aluno pode mandar de novo.
    }
  }

  return { estado, tentativas, feedback, enviando: submissao.isPending, enviar }
}

export function useSubmeterResposta(atividadeId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (resposta: RespostaDoAluno) => submeterResposta(atividadeId, resposta),
    onSuccess: (correcao) => {
      void queryClient.invalidateQueries({
        queryKey: chaves.atividades.tentativas(atividadeId),
      })
      // Toda tentativa soma minutos na meta do dia, acertando ou não.
      void queryClient.invalidateQueries({ queryKey: chaves.gamificacao.metaDiaria() })
      // O ✓ da atividade no mapa e no detalhe do módulo.
      if (correcao.correta) void queryClient.invalidateQueries({ queryKey: chaves.trilhas.todas })
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
      // O passo fechado muda progresso, catálogo, detalhe, ranking e, no último
      // passo de uma trilha de parceiro, os certificados.
      void queryClient.invalidateQueries({ queryKey: chaves.trilhas.todas })
      void queryClient.invalidateQueries({ queryKey: chaves.certificados.todas })
      void queryClient.invalidateQueries({ queryKey: chaves.perfil.todas })
      void queryClient.invalidateQueries({ queryKey: chaves.ranking.todas })
      void queryClient.invalidateQueries({ queryKey: chaves.gamificacao.todas })
    },
  })
}

export function useReportarPasso(slug: string | undefined) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (ordem: number) => reportarPasso(slug as string, ordem),
    onSuccess: (resultado) => {
      // O módulo removido some da trilha, do catálogo e da trilha guiada.
      if (resultado.removido) void queryClient.invalidateQueries({ queryKey: chaves.trilhas.todas })
    },
  })
}

/** Gerar leva segundos: enquanto a geração roda, pergunta de novo. */
const INTERVALO_DA_GERACAO = 4000

export function useExercicios(slug: string | undefined, ordem: number, habilitado: boolean) {
  return useQuery({
    queryKey: chaves.trilhas.exercicios(slug ?? '', ordem),
    queryFn: () => buscarExercicios(slug as string, ordem),
    // Só quando o aluno pede: abrir o passo não dispara a geração.
    enabled: habilitado && Boolean(slug),
    refetchInterval: (query) =>
      query.state.data?.status === 'gerando' ? INTERVALO_DA_GERACAO : false,
  })
}
