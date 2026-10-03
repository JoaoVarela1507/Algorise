/**
 * Chamadas das rotas de trilha (`/api/v1/trilhas`).
 *
 * Os tipos saem do OpenAPI (`npm run gen:api`): mudar um schema no backend e
 * esquecer o frontend vira erro de compilação, não bug em produção.
 */
import { apiGet, apiPost } from '@/services/api'
import type { components } from '@/types/api'
import type { CategoriaTrilha, TrilhaResumo } from '@/types/trilha'

export type TrilhaApi = components['schemas']['Trilha']
export type TrilhaDetalheApi = components['schemas']['TrilhaDetalhe']
export type TrilhaRecomendadaApi = components['schemas']['TrilhaRecomendada']
export type PassoApi = components['schemas']['PassoDetalhe']
export type PaginaTrilhas = components['schemas']['Pagina_Trilha_']

export interface FiltrosCatalogo {
  busca?: string
  /** A tela 25 deixa marcar vários; a API aceita o parâmetro repetido. */
  periodos?: number[]
  categoria?: string
  pagina?: number
  tamanhoPagina?: number
}

function querystring(filtros: FiltrosCatalogo): string {
  const params = new URLSearchParams()
  if (filtros.busca?.trim()) params.set('busca', filtros.busca.trim())
  for (const periodo of filtros.periodos ?? []) params.append('periodo', String(periodo))
  if (filtros.categoria) params.set('categoria', filtros.categoria)
  if (filtros.pagina) params.set('pagina', String(filtros.pagina))
  if (filtros.tamanhoPagina) params.set('tamanho_pagina', String(filtros.tamanhoPagina))

  const texto = params.toString()
  return texto ? `?${texto}` : ''
}

export function buscarCatalogo(filtros: FiltrosCatalogo = {}): Promise<PaginaTrilhas> {
  return apiGet<PaginaTrilhas>(`/trilhas${querystring(filtros)}`)
}

export function buscarRecomendadas(): Promise<TrilhaRecomendadaApi[]> {
  return apiGet<TrilhaRecomendadaApi[]>('/trilhas/recomendadas')
}

export function buscarTrilha(slug: string): Promise<TrilhaDetalheApi> {
  return apiGet<TrilhaDetalheApi>(`/trilhas/${slug}`)
}

export function buscarPasso(slug: string, ordem: number): Promise<PassoApi> {
  return apiGet<PassoApi>(`/trilhas/${slug}/passos/${ordem}`)
}

export function iniciarTrilha(slug: string): Promise<TrilhaDetalheApi> {
  return apiPost<TrilhaDetalheApi>(`/trilhas/${slug}/iniciar`, {})
}

// As categorias que o card sabe colorir. Trilha com categoria nova (ou sem
// categoria) cai em "Gerais" em vez de quebrar a tela.
const CATEGORIAS: CategoriaTrilha[] = [
  'Linguagens',
  'Gerais',
  'Fundamentos',
  'Infraestrutura',
  'Dados',
]

/**
 * Converte a trilha da API para o formato que o `TrilhaCard` espera.
 *
 * As duas formas existem por motivos diferentes: a da API é o contrato, a da
 * tela é o que o componente precisa desenhar. Traduzir aqui mantém a tela livre
 * de `snake_case` e o contrato livre de detalhe de UI.
 */
export function paraCard(
  trilha: TrilhaApi | TrilhaRecomendadaApi,
  opcoes: { motivo?: string; recomendada?: boolean } = {},
): TrilhaResumo {
  const motivo = opcoes.motivo ?? ('motivo' in trilha ? trilha.motivo : '') ?? ''

  return {
    id: trilha.slug,
    nome: trilha.nome,
    categoria: CATEGORIAS.find((c) => c === trilha.categoria) ?? 'Gerais',
    periodo: trilha.periodo ?? 1,
    modulosConcluidos: trilha.progresso,
    // Trilha sem módulo ainda cadastrado dividiria por zero no card.
    totalModulos: Math.max(trilha.total_modulos, 1),
    motivo,
    recomendada: opcoes.recomendada ?? 'motivo' in trilha,
    // O desbloqueio por pré-requisito entre trilhas ainda não existe no
    // backend; hoje o que trava é o passo dentro da trilha (#29).
    bloqueada: false,
  }
}
