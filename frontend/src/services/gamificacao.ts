/** Chamadas da gamificação (`/api/v1/gamificacao`), das telas 16 e 20. */
import { apiGet, apiPost } from '@/services/api'
import type { components } from '@/types/api'

export type PainelApi = components['schemas']['Painel']

export function buscarPainel(): Promise<PainelApi> {
  return apiGet<PainelApi>('/gamificacao/me')
}

/** Registra o acesso do dia; chamar várias vezes no mesmo dia conta uma só. */
export function registrarCheckin(): Promise<PainelApi> {
  return apiPost<PainelApi>('/gamificacao/checkin', {})
}
