import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PlayerYoutube } from '@/components/trilha/PlayerYoutube'

const URL_VIDEO = 'https://www.youtube.com/watch?v=abcdefghijk'

function mensagemDoPlayer(iframe: HTMLIFrameElement, dados: unknown, origem: string) {
  window.dispatchEvent(
    new MessageEvent('message', {
      data: JSON.stringify(dados),
      origin: origem,
      source: iframe.contentWindow,
    }),
  )
}

describe('PlayerYoutube (#21)', () => {
  it('avisa quando o player diz que o vídeo terminou', () => {
    const aoTerminar = vi.fn()
    const { container } = render(
      <PlayerYoutube url={URL_VIDEO} titulo="Aula" aoTerminar={aoTerminar} />,
    )
    const iframe = container.querySelector('iframe') as HTMLIFrameElement

    mensagemDoPlayer(
      iframe,
      { event: 'onStateChange', info: 1 },
      'https://www.youtube-nocookie.com',
    )
    expect(aoTerminar).not.toHaveBeenCalled()

    mensagemDoPlayer(
      iframe,
      { event: 'onStateChange', info: 0 },
      'https://www.youtube-nocookie.com',
    )
    expect(aoTerminar).toHaveBeenCalledOnce()
  })

  it('ignora mensagem de outra origem', () => {
    const aoTerminar = vi.fn()
    const { container } = render(
      <PlayerYoutube url={URL_VIDEO} titulo="Aula" aoTerminar={aoTerminar} />,
    )
    const iframe = container.querySelector('iframe') as HTMLIFrameElement

    mensagemDoPlayer(iframe, { event: 'onStateChange', info: 0 }, 'https://site-qualquer.com')

    expect(aoTerminar).not.toHaveBeenCalled()
  })
})
