/** Chamadas da gamificação (`/api/v1/gamificacao`), das telas 16 e 20. */
import { apiGet, apiPost } from '@/services/api'
import type { components } from '@/types/api'
import type { Conquista, MetaDiaria } from '@/types/gamificacao'

export type PainelApi = components['schemas']['Painel']
export type MetaDiariaApi = components['schemas']['MetaDiaria']

export function buscarPainel(): Promise<PainelApi> {
  return apiGet<PainelApi>('/gamificacao/me')
}

/** Registra o acesso do dia; chamar várias vezes no mesmo dia conta uma só. */
export function registrarCheckin(): Promise<PainelApi> {
  return apiPost<PainelApi>('/gamificacao/checkin', {})
}

export function buscarMetaDiaria(): Promise<MetaDiariaApi> {
  return apiGet<MetaDiariaApi>('/gamificacao/meta-diaria')
}

/** Já vem na forma que o card usa: o ícone sai do `id`, lá no componente. */
export function buscarConquistas(): Promise<Conquista[]> {
  return apiGet<Conquista[]>('/gamificacao/conquistas')
}

export function paraMetaDiaria(meta: MetaDiariaApi): MetaDiaria {
  return {
    xpHoje: meta.xp_hoje,
    xpMeta: meta.xp_meta,
    desafiosResolvidos: meta.desafios_resolvidos,
    minutosEstudados: meta.minutos_estudados,
  }
}
