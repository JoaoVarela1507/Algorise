import type { EntradaRankingApi, RankingApi } from '@/services/ranking'

/**
 * Aplica o `ranking.atualizado` (#37) num ranking em cache, sem buscar a lista
 * de novo. O evento traz só as linhas que mudaram; aqui elas entram no lugar
 * das antigas, e a página continua do mesmo tamanho e na mesma faixa de
 * posições.
 */
export function aplicarMudancas(
  ranking: RankingApi,
  mudancas: EntradaRankingApi[],
  total: number,
  faixa: { deslocamento?: number; limite?: number } = {},
): RankingApi {
  const porId = new Map(mudancas.map((m) => [m.usuario_id, m]))
  const atualizar = (e: EntradaRankingApi) => porId.get(e.usuario_id) ?? e

  const inicio = (faixa.deslocamento ?? 0) + 1
  const tamanho = faixa.limite ?? Math.max(ranking.lista.length, 1)
  const fim = inicio + tamanho - 1
  // Na página fica quem cai na faixa dela, entre os que já estavam e os que mudaram.
  const candidatos = new Map<number, EntradaRankingApi>()
  for (const entrada of [...ranking.lista.map(atualizar), ...mudancas]) {
    candidatos.set(entrada.usuario_id, entrada)
  }
  const lista = [...candidatos.values()]
    .filter((e) => e.posicao >= inicio && e.posicao <= fim)
    .sort((a, b) => a.posicao - b.posicao)

  const doPodio = new Map<number, EntradaRankingApi>()
  for (const entrada of [...ranking.podio.map(atualizar), ...mudancas]) {
    doPodio.set(entrada.usuario_id, entrada)
  }
  const tamanhoPodio = Math.max(ranking.podio.length, 3)
  const podio = [...doPodio.values()]
    .filter((e) => e.posicao <= tamanhoPodio)
    .sort((a, b) => a.posicao - b.posicao)

  return {
    ...ranking,
    podio,
    lista,
    total,
    usuario: ranking.usuario ? atualizar(ranking.usuario) : ranking.usuario,
  }
}
