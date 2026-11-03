/**
 * Player incorporado do YouTube, tocando só o trecho do módulo (#210).
 *
 * O módulo feito de uma parte de uma aula longa é um intervalo do vídeo, e o
 * player do YouTube aceita esse intervalo pela URL (`start` e `end`, em
 * segundos inteiros). O domínio `youtube-nocookie` não grava cookie de
 * rastreio enquanto o aluno não dá play.
 */
import { idDoVideo, urlDoPlayer } from '@/lib/youtube'

export function PlayerYoutube({
  url,
  titulo,
  inicio,
  fim,
}: {
  url: string
  titulo: string
  inicio?: number | null
  fim?: number | null
}) {
  const id = idDoVideo(url)
  if (!id) return null
  return (
    <div className="aspect-video w-full overflow-hidden rounded-lg border border-border bg-black shadow-sm">
      <iframe
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
