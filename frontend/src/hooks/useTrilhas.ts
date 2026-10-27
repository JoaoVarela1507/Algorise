/**
 * Hooks das trilhas.
 *
 * Busca, filtro e paginação ficam **no servidor**: a API já faz isso (#29), e
 * repetir o filtro aqui só funcionaria enquanto o catálogo coubesse numa página.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { chaves } from '@/lib/query'
import {
  buscarCatalogo,
  buscarPasso,
  buscarRecomendadas,
  buscarTrilha,
  iniciarTrilha,
  paraCard,
  type FiltrosCatalogo,
} from '@/services/trilhas'
import type { TrilhaResumo } from '@/types/trilha'

export interface CatalogoDeTrilhas {
  trilhas: TrilhaResumo[]
  total: number
  totalPaginas: number
  pagina: number
}

export function useCatalogoDeTrilhas(filtros: FiltrosCatalogo = {}) {
  return useQuery({
    queryKey: chaves.trilhas.catalogo(filtros as Record<string, unknown>),
    queryFn: () => buscarCatalogo(filtros),
    select: (pagina): CatalogoDeTrilhas => ({
      trilhas: pagina.itens.map((trilha) => paraCard(trilha)),
      total: pagina.total,
      totalPaginas: pagina.total_paginas,
      pagina: pagina.pagina,
    }),
    // A página anterior continua na tela enquanto a próxima carrega, em vez de
    // a grade piscar vazia a cada clique no paginador.
    placeholderData: (anterior) => anterior,
  })
}

export function useTrilhasRecomendadas(habilitado = true) {
  return useQuery({
    queryKey: chaves.trilhas.recomendadas(),
    queryFn: buscarRecomendadas,
    // Só para quem está logado: a rota exige token.
    enabled: habilitado,
    select: (trilhas) => trilhas.map((trilha) => paraCard(trilha, { recomendada: true })),
  })
}

export function useTrilha(slug: string | undefined) {
  return useQuery({
    queryKey: chaves.trilhas.detalhe(slug ?? ''),
    queryFn: () => buscarTrilha(slug as string),
    enabled: Boolean(slug),
  })
}

export function usePasso(slug: string | undefined, ordem: number | undefined) {
  return useQuery({
    queryKey: chaves.trilhas.passo(slug ?? '', ordem ?? 0),
    queryFn: () => buscarPasso(slug as string, ordem as number),
    enabled: Boolean(slug) && Number.isInteger(ordem),
  })
}

export function useIniciarTrilha() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (slug: string) => iniciarTrilha(slug),
    onSuccess: (trilha) => {
      // A resposta já é o detalhe atualizado: aproveitar evita um ida e volta
      // a mais logo depois do clique.
      queryClient.setQueryData(chaves.trilhas.detalhe(trilha.slug), trilha)
      // O catálogo e as recomendadas mudam de progresso, então são refeitos.
      void queryClient.invalidateQueries({ queryKey: chaves.trilhas.todas })
    },
  })
}
