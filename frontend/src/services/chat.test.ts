/**
 * Leitura do streaming do chat (#11).
 *
 * A rede entrega o SSE em pedaços que não respeitam o fim do evento, nem o fim
 * de um caractere: um "ç" pode chegar partido entre dois. É isso que os testes
 * simulam, quebrando o corpo em lugares ruins de propósito.
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, definirAccessToken } from '@/services/api'
import { lerEventos, perguntarAoTutor } from '@/services/chat'

function evento(nome: string, dados: unknown) {
  return `event: ${nome}\ndata: ${JSON.stringify(dados)}\n\n`
}

/** Corpo que chega nos pedaços dados, em bytes. */
function corpoEmPedacos(pedacos: Uint8Array[]) {
  return new ReadableStream<Uint8Array>({
    start(controle) {
      for (const pedaco of pedacos) controle.enqueue(pedaco)
      controle.close()
    },
  })
}

function partirEm(texto: string, tamanho: number) {
  const bytes = new TextEncoder().encode(texto)
  const pedacos: Uint8Array[] = []
  for (let i = 0; i < bytes.length; i += tamanho) pedacos.push(bytes.slice(i, i + tamanho))
  return pedacos
}

async function todos(corpo: ReadableStream<Uint8Array>) {
  const lidos = []
  for await (const lido of lerEventos(corpo)) lidos.push(lido)
  return lidos
}

const SSE =
  evento('chat.conversa', { conversa_id: 7, titulo: 'Laço', mensagem_id: 1 }) +
  evento('chat.token', { texto: 'Um laço ' }) +
  evento('chat.token', { texto: 'repete ações.' }) +
  evento('chat.fim', { mensagem_id: 2 })

afterEach(() => {
  vi.unstubAllGlobals()
  definirAccessToken(null)
})

describe('lerEventos', () => {
  it('junta eventos e caracteres partidos pela rede', async () => {
    // 3 bytes por vez: corta o "ç" (2 bytes) e todos os eventos no meio.
    const lidos = await todos(corpoEmPedacos(partirEm(SSE, 3)))

    expect(lidos.map((l) => l.evento)).toEqual([
      'chat.conversa',
      'chat.token',
      'chat.token',
      'chat.fim',
    ])
    expect(lidos[1].dados).toEqual({ texto: 'Um laço ' })
  })

  it('ignora bloco sem dados ou com JSON quebrado', async () => {
    const corpo = ': comentário\n\n' + 'event: x\ndata: {quebrado\n\n' + evento('chat.fim', {})

    expect((await todos(corpoEmPedacos(partirEm(corpo, 1000)))).map((l) => l.evento)).toEqual([
      'chat.fim',
    ])
  })
})

describe('perguntarAoTutor', () => {
  it('manda a pergunta com o token e devolve a resposta inteira', async () => {
    const fetchFalso = vi.fn().mockResolvedValue(
      new Response(corpoEmPedacos(partirEm(SSE, 5)), {
        headers: { 'Content-Type': 'text/event-stream' },
      }),
    )
    vi.stubGlobal('fetch', fetchFalso)
    definirAccessToken('token-do-aluno')
    const parciais: string[] = []

    const resposta = await perguntarAoTutor(
      { conteudo: 'O que é um laço?', modo: 'rapido' },
      (parcial) => parciais.push(parcial),
    )

    expect(resposta).toEqual({
      conversaId: 7,
      titulo: 'Laço',
      resposta: 'Um laço repete ações.',
      incompleta: false,
    })
    expect(parciais).toEqual(['Um laço ', 'Um laço repete ações.'])

    const [url, init] = fetchFalso.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/chat/mensagens')
    expect(JSON.parse(init.body as string)).toEqual({
      conversa_id: null,
      conteudo: 'O que é um laço?',
      modo: 'rapido',
    })
    expect(new Headers(init.headers).get('Authorization')).toBe('Bearer token-do-aluno')
  })

  it('sem o chat.fim, a resposta volta como incompleta', async () => {
    const cortado =
      evento('chat.conversa', { conversa_id: 7, titulo: 'Laço', mensagem_id: 1 }) +
      evento('chat.token', { texto: 'Um laço ' }) +
      evento('chat.erro', { code: 'ia_indisponivel', message: 'fora', mensagem_id: 2 })
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response(corpoEmPedacos(partirEm(cortado, 1000)))),
    )

    const resposta = await perguntarAoTutor({ conversaId: 7, conteudo: 'e?', modo: 'medio' })

    expect(resposta).toMatchObject({ resposta: 'Um laço ', incompleta: true })
  })

  it('IA fora do ar sobe como ApiError com a mensagem da API', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            erro: { code: 'ia_indisponivel', message: 'O tutor está fora do ar agora.' },
          }),
          { status: 503, headers: { 'Content-Type': 'application/json' } },
        ),
      ),
    )

    const falha = perguntarAoTutor({ conteudo: 'oi', modo: 'medio' })

    await expect(falha).rejects.toBeInstanceOf(ApiError)
    await expect(falha).rejects.toMatchObject({
      status: 503,
      code: 'ia_indisponivel',
      message: 'O tutor está fora do ar agora.',
    })
  })
})
