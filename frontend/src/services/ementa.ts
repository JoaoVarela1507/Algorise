/**
 * Assuntos da ementa, revisão e trilha guiada (#38).
 *
 * Depois do upload (`enviarEmenta`, em `services/onboarding`), o servidor lê o
 * PDF e a IA lê as disciplinas e os assuntos. O aluno revisa a lista, confirma,
 * e a trilha guiada sai da ementa confirmada.
 */
import { apiGet, apiPost, apiPut } from '@/services/api'
import type { EmentaStatus } from '@/services/onboarding'
import type { components } from '@/types/api'

export type AssuntosDaEmenta = components['schemas']['AssuntosDaEmenta']
export type DisciplinaLida = components['schemas']['DisciplinaLida']
export type DisciplinaRevisada = components['schemas']['DisciplinaRevisada']
export type TrilhaGuiada = components['schemas']['TrilhaGuiada']
export type ItemGuiado = components['schemas']['ItemGuiado']

export function buscarEmentaAtual(): Promise<EmentaStatus> {
  return apiGet<EmentaStatus>('/ementas/atual')
}

export function buscarAssuntos(ementaId: number): Promise<AssuntosDaEmenta> {
  return apiGet<AssuntosDaEmenta>(`/ementas/${ementaId}/assuntos`)
}

/** A lista inteira, como o aluno deixou: o que sai dela é removido no servidor. */
export function revisarAssuntos(
  ementaId: number,
  disciplinas: DisciplinaRevisada[],
): Promise<AssuntosDaEmenta> {
  return apiPut<AssuntosDaEmenta>(`/ementas/${ementaId}/assuntos`, { disciplinas })
}

export function relerAssuntos(ementaId: number): Promise<EmentaStatus> {
  return apiPost<EmentaStatus>(`/ementas/${ementaId}/assuntos`, {})
}

export function confirmarEmenta(ementaId: number): Promise<EmentaStatus> {
  return apiPost<EmentaStatus>(`/ementas/${ementaId}/confirmar`, {})
}

export function buscarTrilhaGuiada(): Promise<TrilhaGuiada> {
  return apiGet<TrilhaGuiada>('/trilha-guiada')
}

/** Ainda há o que ler: o PDF ou os assuntos estão na fila ou sendo lidos. */
export function emLeitura(ementa: EmentaStatus): boolean {
  return (
    ementa.status === 'pendente' ||
    ementa.status === 'processando' ||
    (ementa.status === 'processada' &&
      (ementa.status_assuntos === 'pendente' || ementa.status_assuntos === 'processando'))
  )
}
