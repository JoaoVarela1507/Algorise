/**
 * Player incorporado do YouTube, tocando só o trecho do módulo (#210).
 *
 * O módulo feito de uma parte de uma aula longa é um intervalo do vídeo, e o
 * player do YouTube aceita esse intervalo pela URL (`start` e `end`, em
 * segundos inteiros). O domínio `youtube-nocookie` não grava cookie de
 * rastreio enquanto o aluno não dá play.
 *
 * Avisa quando o vídeo termina (`aoTerminar`), para o passo marcar o vídeo como
 * assistido (#21). Isso vem do próprio player por `postMessage`, o protocolo
 * que a IFrame API do YouTube usa por baixo: assim não precisamos carregar o
 * script dela. Com `end` na URL, "terminou" é o fim do trecho do módulo.
 */
import { useEffect, useRef } from 'react'
import { idDoVideo, urlDoPlayer, VIDEO_TERMINOU } from '@/lib/youtube'

const ORIGENS_DO_PLAYER = ['https://www.youtube-nocookie.com', 'https://www.youtube.com']

export function PlayerYoutube({
  url,
  titulo,
  inicio,
  fim,
  aoTerminar,
}: {
  url: string
  titulo: string
  inicio?: number | null
  fim?: number | null
  aoTerminar?: () => void
}) {
  const id = idDoVideo(url)
  const quadro = useRef<HTMLIFrameElement>(null)
  // Na ref, e não na dependência do efeito: o pai recria a função a cada render.
  const terminou = useRef(aoTerminar)
  terminou.current = aoTerminar

  useEffect(() => {
    const iframe = quadro.current
    if (!iframe || !id) return

    // O player só manda eventos depois de alguém dizer que está ouvindo.
    function ouvir() {
      iframe?.contentWindow?.postMessage(
        JSON.stringify({ event: 'listening', id: 'algorise', channel: 'widget' }),
        '*',
      )
    }

    function receber(evento: MessageEvent) {
      if (!ORIGENS_DO_PLAYER.includes(evento.origin) || evento.source !== iframe?.contentWindow) {
        return
      }
      let dados: { event?: string; info?: unknown }
      try {
        dados = typeof evento.data === 'string' ? JSON.parse(evento.data) : evento.data
      } catch {
        return
      }
      const estado =
        dados.event === 'onStateChange'
          ? dados.info
          : dados.event === 'infoDelivery'
            ? (dados.info as { playerState?: number } | undefined)?.playerState
            : undefined
      if (estado === VIDEO_TERMINOU) terminou.current?.()
    }

    window.addEventListener('message', receber)
    iframe.addEventListener('load', ouvir)
    ouvir()
    return () => {
      window.removeEventListener('message', receber)
      iframe.removeEventListener('load', ouvir)
    }
  }, [id])

  if (!id) return null
  return (
    <div className="aspect-video w-full overflow-hidden rounded-lg border border-border bg-black shadow-sm">
      <iframe
        ref={quadro}
        src={urlDoPlayer(id, inicio, fim)}
        title={`Vídeo: ${titulo}`}
        className="size-full"
        allow="accelerometer; encrypted-media; gyroscope; picture-in-picture"
        allowFullScreen
        loading="lazy"
      />
    </div>
  )
}
