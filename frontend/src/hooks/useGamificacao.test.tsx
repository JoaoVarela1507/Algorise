/**
 * Testes dos hooks de gamificação.
 *
 * O check-in é o que mais importa: ele roda ao abrir a home, e um efeito mal
 * escrito aqui viraria uma requisição por render.
 */
import { QueryClientProvider, type QueryClient } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useCheckin, usePainel } from '@/hooks/useGamificacao'
import { criarQueryClient } from '@/lib/query'

const PAINEL = {
  xp_total: 120,
  nivel: 2,
  xp_no_nivel: 70,
  xp_para_o_proximo: 80,
  streak_dias: 3,
  maior_streak: 7,
}

function resposta(corpo: unknown) {
  return new Response(JSON.stringify(corpo), {
    status: 200,
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

describe('painel', () => {
  it('traz XP, nível e streak', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(resposta(PAINEL)))

    const { result } = renderHook(() => usePainel(), { wrapper: Envolvido })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toMatchObject({ nivel: 2, streak_dias: 3 })
  })

  it('não busca quando desabilitado', () => {
    const fetchFalso = vi.fn()
    vi.stubGlobal('fetch', fetchFalso)

    renderHook(() => usePainel(false), { wrapper: Envolvido })

    expect(fetchFalso).not.toHaveBeenCalled()
  })
})

describe('check-in', () => {
  it('aproveita a resposta como painel, sem buscar de novo', async () => {
    const fetchFalso = vi.fn().mockResolvedValue(resposta({ ...PAINEL, streak_dias: 4 }))
    vi.stubGlobal('fetch', fetchFalso)

    const { result } = renderHook(() => useCheckin(), { wrapper: Envolvido })
    result.current.mutate()

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(queryClient.getQueryData(['gamificacao', 'painel'])).toMatchObject({ streak_dias: 4 })
    expect(fetchFalso).toHaveBeenCalledTimes(1)
  })

  it('bate no endpoint de check-in', async () => {
    const fetchFalso = vi.fn().mockResolvedValue(resposta(PAINEL))
    vi.stubGlobal('fetch', fetchFalso)

    const { result } = renderHook(() => useCheckin(), { wrapper: Envolvido })
    result.current.mutate()

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(fetchFalso.mock.calls[0][0]).toContain('/gamificacao/checkin')
  })
})
