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
    const url = new URL(urlDoPlayer('abc', 60.4, 599.2))
    expect(url.origin + url.pathname).toBe('https://www.youtube-nocookie.com/embed/abc')
    expect(url.searchParams.get('start')).toBe('60')
    expect(url.searchParams.get('end')).toBe('600')
  })

  it('sem intervalo, o vídeo inteiro', () => {
    const url = new URL(urlDoPlayer('abc'))
    expect(url.searchParams.has('start')).toBe(false)
    expect(url.searchParams.has('end')).toBe(false)
  })

  it('liga as legendas em português e os eventos do player (#21)', () => {
    const url = new URL(urlDoPlayer('abc'))
    expect(url.searchParams.get('cc_load_policy')).toBe('1')
    expect(url.searchParams.get('cc_lang_pref')).toBe('pt')
    expect(url.searchParams.get('enablejsapi')).toBe('1')
    expect(url.searchParams.get('origin')).toBe(window.location.origin)
  })
})
