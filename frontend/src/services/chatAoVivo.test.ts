/**
 * Pergunta ao tutor pelo WebSocket (#36), e o fallback em SSE quando a
 * conexão não está aberta. O socket é falso; o SSE é trocado por um mock.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/services/api'
import { perguntar } from '@/services/chatAoVivo'
import { ClienteTempoReal } from '@/services/tempoReal'

const perguntarAoTutor = vi.hoisted(() => vi.fn())
vi.mock('@/services/chat', () => ({ perguntarAoTutor }))

class SocketFalso {
  static ultimo: SocketFalso
  readyState = 0
  enviados: Record<string, unknown>[] = []
  onopen: ((ev: Event) => void) | null = null
  onmessage: ((ev: MessageEvent) => void) | null = null
  onclose: ((ev: CloseEvent) => void) | null = null
  onerror: ((ev: Event) => void) | null = null

  constructor() {
    SocketFalso.ultimo = this
  }

  send(dados: string) {
    this.enviados.push(JSON.parse(dados) as Record<string, unknown>)
  }

  close() {
    this.readyState = 3
  }

  receber(mensagem: unknown) {
    this.onmessage?.({ data: JSON.stringify(mensagem) } as MessageEvent)
  }
}

function evento(canal: string, nome: string, payload: Record<string, unknown> = {}) {
  return { tipo: 'evento', canal, evento: nome, payload }
}

/** Um cliente já conectado e autenticado. */
function conectado() {
  const cliente = new ClienteTempoReal({
    token: () => 't',
    renovar: async () => true,
    criarSocket: () => new SocketFalso(),
    url: 'ws://teste/ws',
  })
  cliente.ligar()
  const socket = SocketFalso.ultimo
  socket.readyState = 1
  socket.onopen?.(new Event('open'))
  socket.receber({ tipo: 'autenticado', usuario_id: 1 })
  return { cliente, socket }
}

const pedido = { conteudo: 'O que é um laço?', modo: 'medio' as const }

beforeEach(() => {
  perguntarAoTutor.mockReset()
})

describe('perguntar pelo WebSocket', () => {
  it('conversa nova: pega o canal pelo chat.conversa e junta os pedaços', async () => {
    const { cliente, socket } = conectado()
    const parciais: string[] = []

    const { resposta } = perguntar(cliente, pedido, (p) => parciais.push(p))
    socket.receber({ tipo: 'inscrito', canal: 'chat:9' })
    socket.receber(evento('chat:9', 'chat.conversa', { conversa_id: 9, titulo: 'Laços' }))
    socket.receber(evento('chat:9', 'chat.token', { texto: 'Olá' }))
    socket.receber(evento('chat:9', 'chat.token', { texto: ', aluno' }))
    socket.receber(evento('chat:9', 'chat.fim', { mensagem_id: 3 }))

    await expect(resposta).resolves.toEqual({
      conversaId: 9,
      titulo: 'Laços',
      resposta: 'Olá, aluno',
      incompleta: false,
    })
    expect(parciais).toEqual(['Olá', 'Olá, aluno'])
    expect(socket.enviados).toContainEqual({
      tipo: 'chat.mensagem.enviar',
      conteudo: 'O que é um laço?',
      conversa_id: null,
      modo: 'medio',
    })
  })

  it('conversa existente: inscreve antes e ignora as outras conversas', async () => {
    const { cliente, socket } = conectado()

    const { resposta } = perguntar(cliente, { ...pedido, conversaId: 4 })
    socket.receber(evento('chat:7', 'chat.token', { texto: 'de outra' }))
    socket.receber(evento('chat:4', 'chat.token', { texto: 'minha' }))
    socket.receber(evento('chat:4', 'chat.fim'))

    expect((await resposta).resposta).toBe('minha')
    expect(socket.enviados).toContainEqual({ tipo: 'inscrever', canal: 'chat:4' })
  })

  it('parar manda chat.parar e devolve o parcial incompleto', async () => {
    const { cliente, socket } = conectado()

    const pergunta = perguntar(cliente, { ...pedido, conversaId: 4 })
    socket.receber(evento('chat:4', 'chat.token', { texto: 'meio' }))
    pergunta.parar()
    socket.receber(evento('chat:4', 'chat.parado', { mensagem_id: 5 }))

    expect(socket.enviados).toContainEqual({ tipo: 'chat.parar', conversa_id: 4 })
    await expect(pergunta.resposta).resolves.toMatchObject({ resposta: 'meio', incompleta: true })
  })

  it('parar antes de saber a conversa espera ela chegar', () => {
    const { cliente, socket } = conectado()

    const pergunta = perguntar(cliente, pedido)
    pergunta.parar()
    socket.receber(evento('chat:2', 'chat.conversa', { conversa_id: 2 }))

    expect(socket.enviados).toContainEqual({ tipo: 'chat.parar', conversa_id: 2 })
  })

  it('erro do chat vira ApiError com o status equivalente', async () => {
    const { cliente, socket } = conectado()

    const { resposta } = perguntar(cliente, pedido)
    socket.receber({ tipo: 'erro', code: 'ia_indisponivel', message: 'O tutor está fora do ar' })

    const erro = await resposta.catch((e: unknown) => e)
    expect(erro).toBeInstanceOf(ApiError)
    expect(erro).toMatchObject({ status: 503, code: 'ia_indisponivel' })
  })

  it('conexão que cai no meio devolve o que chegou, incompleto', async () => {
    const { cliente, socket } = conectado()

    const { resposta } = perguntar(cliente, { ...pedido, conversaId: 4 })
    socket.receber(evento('chat:4', 'chat.token', { texto: 'parte' }))
    socket.onclose?.({ code: 1006 } as CloseEvent)

    await expect(resposta).resolves.toMatchObject({ resposta: 'parte', incompleta: true })
    cliente.desligar()
  })
})

describe('fallback em SSE', () => {
  it('sem conexão aberta, usa o POST em SSE e parar corta a requisição', async () => {
    const cliente = new ClienteTempoReal({ token: () => null, renovar: async () => false })
    perguntarAoTutor.mockResolvedValue({
      conversaId: 1,
      titulo: 't',
      resposta: 'x',
      incompleta: true,
    })

    const pergunta = perguntar(cliente, pedido)
    pergunta.parar()

    await expect(pergunta.resposta).resolves.toMatchObject({ incompleta: true })
    const sinal = perguntarAoTutor.mock.calls[0][2] as AbortSignal
    expect(sinal.aborted).toBe(true)
  })
})
