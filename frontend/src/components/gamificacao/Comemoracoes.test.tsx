import { act, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { Comemoracoes } from '@/components/gamificacao/Comemoracoes'
import { USUARIO_TESTE } from '@/lib/loginTeste'
import { chaves } from '@/lib/query'
import type { PainelApi } from '@/services/gamificacao'
import { useAuthStore } from '@/stores/useAuthStore'

function painel(nivel: number, maiorStreak: number): PainelApi {
  return {
    xp_total: nivel * 100,
    nivel,
    xp_no_nivel: 0,
    xp_para_o_proximo: 100,
    streak_dias: maiorStreak,
    maior_streak: maiorStreak,
  } as PainelApi
}

function montar(queryClient: QueryClient) {
  return render(
    <QueryClientProvider client={queryClient}>
      <Comemoracoes />
    </QueryClientProvider>,
  )
}

describe('Comemoracoes', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    localStorage.clear()
    useAuthStore.setState({ usuario: USUARIO_TESTE })
    queryClient = new QueryClient()
  })

  afterEach(() => {
    useAuthStore.setState({ usuario: null })
  })

  it('na primeira vez só guarda: não comemora o que o aluno já tinha', () => {
    queryClient.setQueryData(chaves.gamificacao.painel(), painel(3, 12))
    montar(queryClient)

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('comemora o nível novo quando o painel sobe', async () => {
    queryClient.setQueryData(chaves.gamificacao.painel(), painel(3, 2))
    montar(queryClient)

    act(() => {
      queryClient.setQueryData(chaves.gamificacao.painel(), painel(4, 2))
    })

    expect(await screen.findByRole('dialog', { name: 'Nível 4!' })).toBeInTheDocument()
  })

  it('comemora o recorde de streak, mas não um de 2 dias', async () => {
    queryClient.setQueryData(chaves.gamificacao.painel(), painel(1, 1))
    montar(queryClient)

    await act(async () => {
      queryClient.setQueryData(chaves.gamificacao.painel(), painel(1, 2))
    })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    act(() => {
      queryClient.setQueryData(chaves.gamificacao.painel(), painel(1, 3))
    })
    expect(await screen.findByRole('dialog', { name: '3 dias seguidos!' })).toBeInTheDocument()
  })
})
