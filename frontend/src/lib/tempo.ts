export function saudacaoDoHorario(hora = new Date().getHours()) {
  if (hora < 12) return 'Bom dia'
  if (hora < 18) return 'Boa tarde'
  return 'Boa noite'
}

const relativo = new Intl.RelativeTimeFormat('pt-BR', { numeric: 'auto' })

/** "agora", "há 30 minutos", "ontem", "há 2 dias"… */
export function tempoRelativo(timestamp: number, agora = Date.now()) {
  const segundos = Math.round((timestamp - agora) / 1000)
  const abs = Math.abs(segundos)
  if (abs < 60) return 'agora'
  if (abs < 3600) return relativo.format(Math.round(segundos / 60), 'minute')
  if (abs < 86400) return relativo.format(Math.round(segundos / 3600), 'hour')
  if (abs < 86400 * 30) return relativo.format(Math.round(segundos / 86400), 'day')
  return relativo.format(Math.round(segundos / (86400 * 30)), 'month')
}
