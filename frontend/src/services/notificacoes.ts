/** Centro de notificações (`/api/v1/notificacoes`, #37). */
import { apiGet, apiPost } from '@/services/api'
import type { components } from '@/types/api'

export type Notificacao = components['schemas']['NotificacaoSaida']
type PaginaDeNotificacoes = components['schemas']['Pagina_NotificacaoSaida_']

/** Os tipos que chegam ao vivo e também ficam gravados. */
export const TIPOS_DE_NOTIFICACAO = [
  'conquista.desbloqueada',
  'certificado.liberado',
  'streak.risco',
] as const

export function listarNotificacoes(tamanhoPagina = 20): Promise<PaginaDeNotificacoes> {
  return apiGet<PaginaDeNotificacoes>(`/notificacoes?tamanho_pagina=${tamanhoPagina}`)
}

export async function contarNaoLidas(): Promise<number> {
  const { nao_lidas } = await apiGet<{ nao_lidas: number }>('/notificacoes/contagem')
  return nao_lidas
}

export function marcarLida(id: number): Promise<Notificacao> {
  return apiPost<Notificacao>(`/notificacoes/${id}/lida`, {})
}

export function marcarTodasLidas(): Promise<{ marcadas: number }> {
  return apiPost<{ marcadas: number }>('/notificacoes/lidas', {})
}
