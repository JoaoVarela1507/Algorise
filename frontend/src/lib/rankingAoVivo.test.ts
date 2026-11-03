/** O delta do `ranking.atualizado` (#37) entrando no ranking em cache. */
import { describe, expect, it } from 'vitest'
import { aplicarMudancas } from '@/lib/rankingAoVivo'
import type { EntradaRankingApi, RankingApi } from '@/services/ranking'

function linha(usuario_id: number, posicao: number, xp: number): EntradaRankingApi {
  return { usuario_id, posicao, xp, username: `u${usuario_id}`, nome_exibicao: `U${usuario_id}` }
}

const RANKING: RankingApi = {
  podio: [linha(1, 1, 90), linha(2, 2, 80), linha(3, 3, 70)],
  lista: [linha(4, 4, 60), linha(5, 5, 50), linha(6, 6, 40)],
  total: 6,
  usuario: linha(6, 6, 40),
}

describe('aplicarMudancas', () => {
  it('troca quem mudou de lugar e mantém o resto', () => {
    const novo = aplicarMudancas(RANKING, [linha(6, 4, 65), linha(4, 5, 60), linha(5, 6, 50)], 6, {
      deslocamento: 3,
      limite: 3,
    })

    expect(novo.lista.map((e) => [e.usuario_id, e.posicao])).toEqual([
      [6, 4],
      [4, 5],
      [5, 6],
    ])
    expect(novo.usuario).toMatchObject({ posicao: 4, xp: 65 })
    expect(novo.podio).toEqual(RANKING.podio)
  })

  it('quem sobe ao pódio entra nele e sai da página de baixo', () => {
    const novo = aplicarMudancas(
      RANKING,
      [linha(4, 1, 95), linha(1, 2, 90), linha(2, 3, 80), linha(3, 4, 70)],
      6,
      { deslocamento: 3, limite: 3 },
    )

    expect(novo.podio.map((e) => e.usuario_id)).toEqual([4, 1, 2])
    expect(novo.lista.map((e) => e.usuario_id)).toEqual([3, 5, 6])
  })

  it('alguém novo no ranking atualiza o total', () => {
    const novo = aplicarMudancas(RANKING, [linha(7, 7, 10)], 7)

    expect(novo.total).toBe(7)
    // Fora da faixa da página: não entra nela.
    expect(novo.lista.map((e) => e.usuario_id)).not.toContain(7)
  })
})
