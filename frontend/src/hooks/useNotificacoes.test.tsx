/**
 * Eventos de gamificação ao vivo (#37) e o centro de notificações.
 */
import { QueryClientProvider, type QueryClient } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { CentroNotificacoes } from '@/components/layout/CentroNotificacoes'
import { aplicarNoCache, tratarNotificacao } from '@/hooks/useNotificacoes'
import { chaves, criarQueryClient } from '@/lib/query'
import type { RankingApi } from '@/services/ranking'
import { useAuthStore } from '@/stores/useAuthStore'
import { USUARIO_TESTE } from '@/lib/loginTeste'

const toast = vi.hoisted(() => vi.fn())
vi.mock('@/components/ui/toaster', () => ({ toast }))

let queryClient: QueryClient

beforeEach(() => {
  queryClient = criarQueryClient()
  toast.mockReset()
})

afterEach(() => {
  queryClient.clear()
  vi.unstubAllGlobals()
  useAuthStore.setState({ usuario: null })
})

function resposta(corpo: unknown) {
  return new Response(JSON.stringify(corpo), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('eventos ao vivo', () => {
  it('xp.ganho atualiza o painel em cache e mostra o ganho', () => {
    queryClient.setQueryData(chaves.gamificacao.painel(), {
      xp_total: 40,
      nivel: 1,
      xp_no_nivel: 40,
      xp_para_o_proximo: 10,
      streak_dias: 2,
      maior_streak: 2,
    })

    tratarNotificacao(queryClient, {
      tipo: 'evento',
      canal: 'notificacoes:1',
      evento: 'xp.ganho',
      payload: { valor: 20, xp_total: 60, nivel: 2, xp_no_nivel: 10, xp_para_o_proximo: 140 },
    })

    expect(queryClient.getQueryData(chaves.gamificacao.painel())).toMatchObject({
      xp_total: 60,
      nivel: 2,
      streak_dias: 2,
    })
    expect(toast).toHaveBeenCalledWith('+20 XP')
  })

  it('conquista mostra o toast e recarrega o sino', () => {
    const invalidar = vi.spyOn(queryClient, 'invalidateQueries')

    tratarNotificacao(queryClient, {
      tipo: 'evento',
      canal: 'notificacoes:1',
      evento: 'conquista.desbloqueada',
      payload: { titulo: 'Nível 2!', mensagem: 'Continue assim' },
    })

    expect(toast).toHaveBeenCalledWith('Nível 2!', { description: 'Continue assim' })
    expect(invalidar).toHaveBeenCalledWith({ queryKey: chaves.notificacoes.todas })
  })

  it('ranking.atualizado entra em todos os rankings em cache', () => {
    const ranking: RankingApi = {
      podio: [],
      lista: [{ usuario_id: 2, posicao: 1, xp: 10, username: 'b', nome_exibicao: 'B' }],
      total: 1,
      usuario: null,
    }
    queryClient.setQueryData(chaves.ranking.pagina({ limite: 8 }), ranking)

    aplicarNoCache(queryClient, {
      tipo: 'evento',
      canal: 'ranking:geral',
      evento: 'ranking.atualizado',
      payload: {
        mudancas: [
          { usuario_id: 3, posicao: 1, xp: 30, username: 'c', nome_exibicao: 'C' },
          { usuario_id: 2, posicao: 2, xp: 10, username: 'b', nome_exibicao: 'B' },
        ],
        total: 2,
      },
    })

    const novo = queryClient.getQueryData<RankingApi>(chaves.ranking.pagina({ limite: 8 }))
    expect(novo?.lista.map((e) => e.usuario_id)).toEqual([3, 2])
    expect(novo?.total).toBe(2)
  })
})

describe('centro de notificações', () => {
  it('mostra quantas faltam ler, lista e marca todas como lidas', async () => {
    useAuthStore.setState({ usuario: USUARIO_TESTE })
    let lidas = false
    const fetch = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith('/notificacoes/contagem')) return resposta({ nao_lidas: lidas ? 0 : 2 })
      if (url.endsWith('/notificacoes/lidas') && init?.method === 'POST') {
        lidas = true
        return resposta({ marcadas: 2 })
      }
      return resposta({
        itens: [
          {
            id: 1,
            tipo: 'conquista.desbloqueada',
            titulo: 'Nível 2!',
            mensagem: 'Continue assim',
            dados: {},
            lida_em: null,
            criado_em: new Date().toISOString(),
          },
        ],
        pagina: 1,
        tamanho_pagina: 20,
        total: 1,
        total_paginas: 1,
      })
    })
    vi.stubGlobal('fetch', fetch)
    render(
      <QueryClientProvider client={queryClient}>
        <CentroNotificacoes />
      </QueryClientProvider>,
    )

    const sino = await screen.findByRole('button', { name: 'Notificações, 2 não lidas' })
    await userEvent.click(sino)
    expect(await screen.findByText('Nível 2!')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Marcar todas como lidas' }))

    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Notificações' })).toBeInTheDocument(),
    )
  })
})
