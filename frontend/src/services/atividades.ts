/** Chamadas das atividades e submissões (`/api/v1/atividades`). */
import { apiGet, apiPost } from '@/services/api'
import type { components } from '@/types/api'

export type AtividadeApi = components['schemas']['AtividadeResumo']
export type CorrecaoApi = components['schemas']['Correcao']
export type TentativaApi = components['schemas']['Tentativa']
export type PassoConcluidoApi = components['schemas']['PassoConcluido']

export interface RespostaDoAluno {
  conteudo: string
  tempoGastoSegundos?: number
}

export function buscarAtividade(id: number): Promise<AtividadeApi> {
  return apiGet<AtividadeApi>(`/atividades/${id}`)
}

export function submeterResposta(id: number, resposta: RespostaDoAluno): Promise<CorrecaoApi> {
  return apiPost<CorrecaoApi>(`/atividades/${id}/submissoes`, {
    conteudo: resposta.conteudo,
    tempo_gasto_segundos: resposta.tempoGastoSegundos,
  })
}

export function buscarTentativas(id: number): Promise<TentativaApi[]> {
  return apiGet<TentativaApi[]>(`/atividades/${id}/submissoes`)
}

export function concluirPasso(slug: string, ordem: number): Promise<PassoConcluidoApi> {
  return apiPost<PassoConcluidoApi>(`/trilhas/${slug}/passos/${ordem}/concluir`, {})
}
