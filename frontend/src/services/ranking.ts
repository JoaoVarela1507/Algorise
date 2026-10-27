/** Chamadas do ranking (`/api/v1/ranking`), das telas 16 e 17. */
import { apiGet } from '@/services/api'
import type { components } from '@/types/api'
import type { PosicaoRanking } from '@/types/ranking'

export type RankingApi = components['schemas']['Ranking']
export type EntradaRankingApi = components['schemas']['EntradaRanking']

export interface FiltrosRanking {
  limite?: number
  deslocamento?: number
  usuarioId?: number
}

export function buscarRanking(filtros: FiltrosRanking = {}): Promise<RankingApi> {
  const params = new URLSearchParams()
  if (filtros.limite) params.set('limite', String(filtros.limite))
  if (filtros.deslocamento) params.set('deslocamento', String(filtros.deslocamento))
  if (filtros.usuarioId) params.set('usuario_id', String(filtros.usuarioId))

  const texto = params.toString()
  return apiGet<RankingApi>(`/ranking${texto ? `?${texto}` : ''}`)
}

/** Converte uma linha da API para o formato que o `RankingCard` desenha. */
export function paraLinha(entrada: EntradaRankingApi): PosicaoRanking {
  return {
    usuarioId: String(entrada.usuario_id),
    nome: entrada.nome_exibicao,
    xp: entrada.xp,
    posicao: entrada.posicao,
  }
}

/**
 * Pódio e lista numa sequência só, sem repetir ninguém.
 *
 * A API devolve as duas separadas porque a tela 16 destaca o pódio; o card da
 * home mostra uma lista contínua, e o aluno entra nela mesmo quando a posição
 * dele está longe da primeira página.
 */
export function paraLista(ranking: RankingApi): PosicaoRanking[] {
  const vistos = new Set<number>()
  const linhas: PosicaoRanking[] = []

  for (const entrada of [...ranking.podio, ...ranking.lista]) {
    if (vistos.has(entrada.usuario_id)) continue
    vistos.add(entrada.usuario_id)
    linhas.push(paraLinha(entrada))
  }

  if (ranking.usuario && !vistos.has(ranking.usuario.usuario_id)) {
    linhas.push(paraLinha(ranking.usuario))
  }

  return linhas.sort((a, b) => a.posicao - b.posicao)
}
