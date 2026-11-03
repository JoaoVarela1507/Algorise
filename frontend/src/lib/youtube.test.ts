import { describe, expect, it } from 'vitest'
import { idDoVideo, urlDoPlayer } from '@/lib/youtube'

describe('idDoVideo', () => {
  it.each([
    ['https://www.youtube.com/watch?v=S9uPNppGsGo', 'S9uPNppGsGo'],
    ['https://youtu.be/S9uPNppGsGo', 'S9uPNppGsGo'],
    ['https://www.youtube-nocookie.com/embed/S9uPNppGsGo?start=3', 'S9uPNppGsGo'],
    ['https://vimeo.com/123', null],
    ['não é url', null],
  ])('%s -> %s', (url, id) => {
    expect(idDoVideo(url)).toBe(id)
  })
})

describe('urlDoPlayer', () => {
  it('toca só o trecho do módulo, em segundos inteiros', () => {
    expect(urlDoPlayer('abc', 60.4, 599.2)).toBe(
      'https://www.youtube-nocookie.com/embed/abc?rel=0&start=60&end=600',
    )
  })

  it('sem intervalo, o vídeo inteiro', () => {
    expect(urlDoPlayer('abc')).toBe('https://www.youtube-nocookie.com/embed/abc?rel=0')
  })
})
