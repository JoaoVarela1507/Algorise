/**
 * Testes dos hooks de trilha.
 *
 * O que importa aqui é o que o cache faz: uma requisição só quando duas telas
 * pedem o mesmo dado, nada de insistir num 404, e invalidação depois da
 * mutation. A tradução para o formato do card entra junto, porque é onde um
 * `snake_case` esquecido vira "undefined" na tela.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { criarQueryClient, deveTentarDeNovo } from '@/lib/query'
import { ApiError } from '@/services/api'
import { useCatalogoDeTrilhas, useIniciarTrilha, useTrilhasRecomendadas } from '@/hooks/useTrilhas'

const TRILHA = {
  id: 1,
  slug: 'introducao-python',
  nome: 'Introdução a Python',
  disciplina: 'Algoritmos',
  categoria: 'Linguagens',
  periodo: 1,
  total_modulos: 10,
  progresso: 3,
}

function pagina(itens: unknown[] = [TRILHA]) {
  return { itens, pagina: 1, tamanho_pagina: 20, total: itens.length, total_paginas: 1 }
}

function respostaJson(corpo: unknown, status = 200) {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

let queryClient: QueryClient

function Envolvido({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

beforeEach(() => {
  queryClient = criarQueryClient()
})

afterEach(() => {
  queryClient.clear()
  vi.unstubAllGlobals()
})

describe('catálogo', () => {
  it('traduz a trilha da API para o formato do card', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respostaJson(pagina())))

    const { result } = renderHook(() => useCatalogoDeTrilhas(), { wrapper: Envolvido })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.trilhas[0]).toMatchObject({
      id: 'introducao-python',
      nome: 'Introdução a Python',
      categoria: 'Linguagens',
      modulosConcluidos: 3,
      totalModulos: 10,
    })
    expect(result.current.data?.total).toBe(1)
  })

  it('manda busca, períodos e página para o servidor', async () => {
    const fetchFalso = vi.fn().mockResolvedValue(respostaJson(pagina()))
    vi.stubGlobal('fetch', fetchFalso)

    const { result } = renderHook(
      () => useCatalogoDeTrilhas({ busca: 'redes', periodos: [1, 3], pagina: 2 }),
      { wrapper: Envolvido },
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const url = fetchFalso.mock.calls[0][0] as string
    expect(url).toContain('busca=redes')
    expect(url).toContain('periodo=1&periodo=3')
    expect(url).toContain('pagina=2')
  })

  it('categoria desconhecida não quebra o card', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(respostaJson(pagina([{ ...TRILHA, categoria: 'Robótica' }]))),
    )

    const { result } = renderHook(() => useCatalogoDeTrilhas(), { wrapper: Envolvido })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.trilhas[0].categoria).toBe('Gerais')
  })

  it('trilha sem módulo não divide por zero', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(respostaJson(pagina([{ ...TRILHA, total_modulos: 0 }]))),
    )

    const { result } = renderHook(() => useCatalogoDeTrilhas(), { wrapper: Envolvido })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.trilhas[0].totalModulos).toBe(1)
  })

  it('duas telas pedindo o mesmo dado fazem uma requisição só', async () => {
    const fetchFalso = vi.fn().mockResolvedValue(respostaJson(pagina()))
    vi.stubGlobal('fetch', fetchFalso)

    const primeira = renderHook(() => useCatalogoDeTrilhas(), { wrapper: Envolvido })
    const segunda = renderHook(() => useCatalogoDeTrilhas(), { wrapper: Envolvido })

    await waitFor(() => expect(primeira.result.current.isSuccess).toBe(true))
    await waitFor(() => expect(segunda.result.current.isSuccess).toBe(true))
    expect(fetchFalso).toHaveBeenCalledTimes(1)
  })
})

describe('recomendadas', () => {
  it('não chama a API quando o aluno não está logado', () => {
    const fetchFalso = vi.fn()
    vi.stubGlobal('fetch', fetchFalso)

    renderHook(() => useTrilhasRecomendadas(false), { wrapper: Envolvido })

    expect(fetchFalso).not.toHaveBeenCalled()
  })

  it('marca como recomendada e leva o motivo', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(respostaJson([{ ...TRILHA, motivo: 'Combina com o seu período' }])),
    )

    const { result } = renderHook(() => useTrilhasRecomendadas(), { wrapper: Envolvido })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.[0]).toMatchObject({
      recomendada: true,
      motivo: 'Combina com o seu período',
    })
  })
})

describe('iniciar trilha', () => {
  it('invalida o catálogo depois de iniciar', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respostaJson({ ...TRILHA, modulos: [] })))
    const invalidar = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(() => useIniciarTrilha(), { wrapper: Envolvido })
    result.current.mutate('introducao-python')

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(invalidar).toHaveBeenCalledWith({ queryKey: ['trilhas'] })
  })

  it('aproveita a resposta como detalhe, sem buscar de novo', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respostaJson({ ...TRILHA, modulos: [] })))

    const { result } = renderHook(() => useIniciarTrilha(), { wrapper: Envolvido })
    result.current.mutate('introducao-python')

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(queryClient.getQueryData(['trilhas', 'detalhe', 'introducao-python'])).toMatchObject({
      slug: 'introducao-python',
    })
  })
})

describe('política de nova tentativa', () => {
  it('não insiste em erro do cliente', () => {
    expect(deveTentarDeNovo(0, new ApiError(404, 'não encontrado'))).toBe(false)
    expect(deveTentarDeNovo(0, new ApiError(403, 'bloqueado'))).toBe(false)
  })

  it('insiste em erro do servidor e em falha de rede, até o limite', () => {
    expect(deveTentarDeNovo(0, new ApiError(500, 'erro interno'))).toBe(true)
    expect(deveTentarDeNovo(0, new ApiError(0, 'sem rede'))).toBe(true)
    expect(deveTentarDeNovo(5, new ApiError(500, 'erro interno'))).toBe(false)
  })
})
