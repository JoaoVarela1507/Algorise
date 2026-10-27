/**
 * Testes da tradução do ranking.
 *
 * A API separa pódio e lista porque a tela 16 destaca o pódio; o card da home
 * mostra uma sequência contínua. Juntar as duas é onde nasce o bug clássico de
 * alguém aparecer duas vezes.
 */
import { describe, expect, it } from 'vitest'
import { paraLinha, paraLista, type RankingApi } from '@/services/ranking'

function entrada(posicao: number, nome: string, usuario_id = posicao) {
  return {
    posicao,
    usuario_id,
    username: nome.toLowerCase(),
    nome_exibicao: nome,
    avatar_url: null,
    xp: 1000 - posicao * 10,
  }
}

describe('paraLinha', () => {
  it('traduz os campos que o card desenha', () => {
    expect(paraLinha(entrada(1, 'Ana'))).toEqual({
      usuarioId: '1',
      nome: 'Ana',
      xp: 990,
      posicao: 1,
    })
  })
})

describe('paraLista', () => {
  it('junta pódio e lista sem repetir ninguém', () => {
    const ranking: RankingApi = {
      podio: [entrada(1, 'Ana'), entrada(2, 'Bia'), entrada(3, 'Caio')],
      lista: [entrada(1, 'Ana'), entrada(2, 'Bia'), entrada(3, 'Caio'), entrada(4, 'Davi')],
      total: 4,
      usuario: null,
    }

    const linhas = paraLista(ranking)

    expect(linhas.map((l) => l.nome)).toEqual(['Ana', 'Bia', 'Caio', 'Davi'])
  })

  it('inclui o aluno quando a posição dele está fora da página', () => {
    const ranking: RankingApi = {
      podio: [entrada(1, 'Ana')],
      lista: [entrada(1, 'Ana'), entrada(2, 'Bia')],
      total: 40,
      usuario: entrada(37, 'Você', 99),
    }

    const linhas = paraLista(ranking)

    expect(linhas[linhas.length - 1]).toMatchObject({ nome: 'Você', posicao: 37 })
  })

  it('não duplica o aluno quando ele já está na página', () => {
    const ranking: RankingApi = {
      podio: [entrada(1, 'Ana')],
      lista: [entrada(1, 'Ana'), entrada(2, 'Você', 99)],
      total: 2,
      usuario: entrada(2, 'Você', 99),
    }

    const linhas = paraLista(ranking)

    expect(linhas.filter((l) => l.nome === 'Você')).toHaveLength(1)
  })

  it('devolve em ordem de posição', () => {
    const ranking: RankingApi = {
      podio: [entrada(3, 'Caio'), entrada(1, 'Ana')],
      lista: [entrada(2, 'Bia')],
      total: 3,
      usuario: null,
    }

    expect(paraLista(ranking).map((l) => l.posicao)).toEqual([1, 2, 3])
  })

  it('ranking vazio não quebra', () => {
    expect(paraLista({ podio: [], lista: [], total: 0, usuario: null })).toEqual([])
  })
})
