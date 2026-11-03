/** URLs do YouTube: o id do vídeo e o endereço do player incorporado (#210). */

/** O id do vídeo numa URL do YouTube (`watch?v=`, `youtu.be/` ou `embed/`). */
export function idDoVideo(url: string): string | null {
  try {
    const endereco = new URL(url)
    if (endereco.hostname === 'youtu.be') return endereco.pathname.slice(1) || null
    if (!/(^|\.)youtube(-nocookie)?\.com$/.test(endereco.hostname)) return null
    const doEmbed = endereco.pathname.match(/^\/embed\/([\w-]+)/)
    return doEmbed ? doEmbed[1] : endereco.searchParams.get('v')
  } catch {
    return null
  }
}

/** A URL do player, com o intervalo quando houver. */
export function urlDoPlayer(id: string, inicio?: number | null, fim?: number | null): string {
  const parametros = new URLSearchParams({ rel: '0' })
  if (inicio != null) parametros.set('start', String(Math.floor(inicio)))
  if (fim != null) parametros.set('end', String(Math.ceil(fim)))
  return `https://www.youtube-nocookie.com/embed/${id}?${parametros}`
}
