/**
 * Testes do corpo do `POST /onboarding`.
 *
 * O backend recusa instituição pelo id **e** pelo nome ao mesmo tempo, e curso
 * digitado sem instituição. Quem garante que o frontend nunca manda isso é
 * `corpoDoOnboarding`.
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { definirAccessToken } from '@/services/api'
import { corpoDoOnboarding, enviarEmenta, type DadosOnboarding } from '@/services/onboarding'

const BASE: DadosOnboarding = {
  nivelExperiencia: 'baixo',
  tipoTrilha: 'guiada',
  instituicao: { texto: '', id: null },
  curso: { texto: '', id: null },
}

afterEach(() => vi.unstubAllGlobals())

describe('corpoDoOnboarding', () => {
  it('manda só o id quando a sugestão foi escolhida', () => {
    const corpo = corpoDoOnboarding({
      ...BASE,
      instituicao: { texto: 'Universidade Federal Rural de Pernambuco', id: 1 },
      curso: { texto: 'Bacharelado em Sistemas de Informação', id: 2 },
      periodo: 3,
    })

    expect(corpo).toMatchObject({ instituicao_id: 1, curso_id: 2, periodo: 3 })
    expect(corpo.instituicao).toBeUndefined()
    expect(corpo.curso).toBeUndefined()
  })

  it('manda o texto, sem espaço sobrando, quando foi digitado', () => {
    const corpo = corpoDoOnboarding({
      ...BASE,
      instituicao: { texto: '  Faculdade Nova  ', id: null },
      curso: { texto: 'Engenharia', id: null },
    })

    expect(corpo).toMatchObject({ instituicao: 'Faculdade Nova', curso: 'Engenharia' })
    expect(corpo.instituicao_id).toBeUndefined()
  })

  it('curso digitado com instituição do catálogo vai como texto', () => {
    const corpo = corpoDoOnboarding({
      ...BASE,
      instituicao: { texto: 'UFRPE', id: 1 },
      curso: { texto: 'Licenciatura em Computação', id: null },
    })

    expect(corpo).toMatchObject({ instituicao_id: 1, curso: 'Licenciatura em Computação' })
  })

  it('não manda curso digitado sem instituição', () => {
    const corpo = corpoDoOnboarding({ ...BASE, curso: { texto: 'Sistemas', id: null } })

    expect(corpo.curso).toBeUndefined()
  })
})

describe('enviarEmenta', () => {
  it('sobe o PDF como multipart', async () => {
    definirAccessToken('token')
    const fetchFalso = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: 4, status: 'pendente' }), {
        status: 202,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchFalso)

    const ementa = await enviarEmenta(new File(['%PDF-1.4'], 'ementa.pdf'))

    const [url, init] = fetchFalso.mock.calls[0]
    expect(url).toContain('/api/v1/ementas')
    expect(init.method).toBe('POST')
    expect((init.body as FormData).get('arquivo')).toBeInstanceOf(File)
    expect(ementa.status).toBe('pendente')
  })
})
