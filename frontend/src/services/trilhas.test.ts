import { describe, expect, it } from 'vitest'
import { paraMapa, type TrilhaDetalheApi } from '@/services/trilhas'

type ModuloApi = NonNullable<TrilhaDetalheApi['modulos']>[number]

function modulo(ordem: number, status: ModuloApi['status'], concluidas: boolean[] = []): ModuloApi {
  return {
    id: ordem,
    ordem,
    titulo: `Passo ${ordem}`,
    status,
    xp: 40,
    atividades: concluidas.map((concluida, i) => ({
      id: ordem * 10 + i,
      ordem: i + 1,
      tipo: 'terminal',
      enunciado: `Atividade ${i + 1}`,
      xp: 10,
      concluida,
    })),
  } as ModuloApi
}

function trilha(modulos: ModuloApi[]): TrilhaDetalheApi {
  return {
    id: 1,
    slug: 'python',
    nome: 'Python',
    disciplina: 'Algoritmos',
    periodo: 1,
    total_modulos: modulos.length,
    progresso: modulos.filter((m) => m.status === 'concluido').length,
    modulos,
  } as TrilhaDetalheApi
}

describe('paraMapa', () => {
  it('o primeiro passo aberto é o atual; os outros abertos ficam disponíveis', () => {
    const mapa = paraMapa(
      trilha([
        modulo(1, 'concluido'),
        modulo(2, 'em-andamento'),
        modulo(3, 'em-andamento'),
        modulo(4, 'bloqueado'),
      ]),
    )

    expect(mapa.modulos.map((m) => m.status)).toEqual([
      'concluido',
      'atual',
      'disponivel',
      'bloqueado',
    ])
  })

  it('a próxima atividade é a primeira que falta', () => {
    const [passo] = paraMapa(trilha([modulo(1, 'em-andamento', [true, false, false])])).modulos

    expect(passo.atividades.map((a) => a.status)).toEqual(['feita', 'proxima', 'pendente'])
  })

  it('atividade de passo bloqueado fica bloqueada', () => {
    const [passo] = paraMapa(trilha([modulo(1, 'bloqueado', [false, false])])).modulos

    expect(passo.atividades.every((a) => a.status === 'bloqueada')).toBe(true)
  })

  it('sem tempo sugerido, usa o tempo típico do tipo', () => {
    const [passo] = paraMapa(trilha([modulo(1, 'em-andamento', [false])])).modulos

    expect(passo.atividades[0].minutos).toBe(5)
  })

  it('usa o slug como id, que é o que a rota recebe', () => {
    expect(paraMapa(trilha([])).id).toBe('python')
  })
})
