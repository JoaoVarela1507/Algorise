/** Chamadas do desafio de código (`/api/v1/desafios` e `/execucoes`, #25). */
import { apiGet, apiPost } from '@/services/api'
import type { components } from '@/types/api'

export type DesafioApi = components['schemas']['Desafio']
export type ExecucaoApi = components['schemas']['ExecucaoSaida']
export type ExecucaoNaFilaApi = components['schemas']['ExecucaoNaFila']
export type ResultadoDoCasoApi = components['schemas']['ResultadoDoCaso']

export function buscarDesafio(id: number): Promise<DesafioApi> {
  return apiGet<DesafioApi>(`/desafios/${id}`)
}

/** Manda o código para a sandbox. A resposta é só o id: o resultado sai em `buscarExecucao`. */
export function executarDesafio(id: number, codigo: string): Promise<ExecucaoNaFilaApi> {
  return apiPost<ExecucaoNaFilaApi>(`/desafios/${id}/execucoes`, { codigo })
}

export function buscarExecucao(id: string): Promise<ExecucaoApi> {
  return apiGet<ExecucaoApi>(`/execucoes/${id}`)
}

/** Ainda rodando: a tela continua perguntando. */
export function emAndamento(execucao: Pick<ExecucaoApi, 'status'> | undefined): boolean {
  return execucao?.status === 'na_fila' || execucao?.status === 'executando'
}
