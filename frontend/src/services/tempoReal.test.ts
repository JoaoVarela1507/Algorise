/**
 * Cliente do WebSocket (#35): autenticação no primeiro frame, canais,
 * reconexão exponencial e a fila offline. O socket é falso e os relógios
 * também, para a espera entre tentativas ser exata.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ClienteTempoReal, FECHAMENTO, type OpcoesTempoReal } from '@/services/tempoReal'

class SocketFalso {
  static criados: SocketFalso[] = []
  readyState = 0
  enviados: unknown[] = []
  onopen: ((ev: Event) => void) | null = null
  onmessage: ((ev: MessageEvent) => void) | null = null
  onclose: ((ev: CloseEvent) => void) | null = null
  onerror: ((ev: Event) => void) | null = null

  constructor(readonly url: string) {
    SocketFalso.criados.push(this)
  }

  send(dados: string) {
    this.enviados.push(JSON.parse(dados))
  }

  close() {
    this.readyState = 3
  }

  abrir() {
    this.readyState = 1
    this.onopen?.(new Event('open'))
  }

  receber(mensagem: unknown) {
    this.onmessage?.({ data: JSON.stringify(mensagem) } as MessageEvent)
  }

  cair(codigo = 1006) {
    this.readyState = 3
    this.onclose?.({ code: codigo } as CloseEvent)
  }
}

function ultimo() {
  return SocketFalso.criados[SocketFalso.criados.length - 1]
}

function novoCliente(opcoes: Partial<OpcoesTempoReal> = {}) {
  return new ClienteTempoReal({
    token: () => 'token-1',
    renovar: async () => true,
    criarSocket: (url) => new SocketFalso(url),
    url: 'ws://teste/ws',
    aleatorio: () => 1,
    ...opcoes,
  })
}

/** Abre e autentica a conexão mais recente. */
function conectar() {
  const socket = ultimo()
  socket.abrir()
  socket.receber({ tipo: 'autenticado', usuario_id: 7 })
  return socket
}

beforeEach(() => {
  SocketFalso.criados = []
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('ClienteTempoReal', () => {
  it('manda o token no primeiro frame, e não na URL', () => {
    novoCliente().ligar()
    ultimo().abrir()

    expect(ultimo().url).toBe('ws://teste/ws')
    expect(ultimo().enviados[0]).toEqual({ tipo: 'autenticar', token: 'token-1' })
  })

  it('entrega o evento só a quem ouve o canal', () => {
    const cliente = novoCliente()
    const doRanking = vi.fn()
    const doChat = vi.fn()
    cliente.assinar('ranking:geral', doRanking)
    cliente.assinar('chat:1', doChat)
    cliente.ligar()
    const socket = conectar()

    socket.receber({
      tipo: 'evento',
      canal: 'ranking:geral',
      evento: 'ranking.atualizado',
      payload: {},
    })

    expect(socket.enviados).toContainEqual({ tipo: 'inscrever', canal: 'ranking:geral' })
    expect(doRanking).toHaveBeenCalledOnce()
    expect(doChat).not.toHaveBeenCalled()
  })

  it('cancela a inscrição quando o último ouvinte sai', () => {
    const cliente = novoCliente()
    cliente.ligar()
    const socket = conectar()
    const parar1 = cliente.assinar('ranking:geral', vi.fn())
    const parar2 = cliente.assinar('ranking:geral', vi.fn())

    parar1()
    expect(socket.enviados).not.toContainEqual({ tipo: 'cancelar', canal: 'ranking:geral' })
    parar2()
    expect(socket.enviados).toContainEqual({ tipo: 'cancelar', canal: 'ranking:geral' })
  })

  it('responde ao ping do servidor', () => {
    novoCliente().ligar()
    const socket = conectar()

    socket.receber({ tipo: 'ping' })

    expect(socket.enviados).toContainEqual({ tipo: 'pong' })
  })

  it('reconecta com espera exponencial e refaz as inscrições', () => {
    const estados: string[] = []
    const cliente = novoCliente({ atrasoBase: 100, aoMudarEstado: (e) => estados.push(e) })
    cliente.assinar('chat:3', vi.fn())
    cliente.ligar()
    conectar().cair()

    vi.advanceTimersByTime(99)
    expect(SocketFalso.criados).toHaveLength(1)
    vi.advanceTimersByTime(1)
    expect(SocketFalso.criados).toHaveLength(2)

    ultimo().cair()
    vi.advanceTimersByTime(199)
    expect(SocketFalso.criados).toHaveLength(2)
    vi.advanceTimersByTime(1)
    expect(SocketFalso.criados).toHaveLength(3)

    const socket = conectar()
    expect(socket.enviados).toContainEqual({ tipo: 'inscrever', canal: 'chat:3' })
    expect(estados).toEqual(['conectando', 'aberto', 'reconectando', 'aberto'])
  })

  it('a espera tem teto', () => {
    const cliente = novoCliente({ atrasoBase: 100, atrasoMaximo: 300 })
    cliente.ligar()
    for (let i = 0; i < 5; i++) {
      ultimo().cair()
      vi.advanceTimersByTime(300)
    }

    expect(SocketFalso.criados).toHaveLength(6)
  })

  it('guarda o que foi enviado offline e manda quando volta', () => {
    const cliente = novoCliente()
    cliente.ligar()

    cliente.enviar({ tipo: 'ping' })
    const socket = conectar()

    expect(socket.enviados).toEqual([{ tipo: 'autenticar', token: 'token-1' }, { tipo: 'ping' }])
  })

  it('renova a sessão quando o servidor recusa o token', async () => {
    let token = 'velho'
    const renovar = vi.fn(async () => {
      token = 'novo'
      return true
    })
    const cliente = novoCliente({ token: () => token, renovar, atrasoBase: 100 })
    cliente.ligar()
    ultimo().abrir()

    ultimo().cair(FECHAMENTO.naoAutenticado)
    await vi.runAllTimersAsync()
    ultimo().abrir()

    expect(renovar).toHaveBeenCalledOnce()
    expect(ultimo().enviados[0]).toEqual({ tipo: 'autenticar', token: 'novo' })
  })

  it('desiste quando a renovação falha', async () => {
    const cliente = novoCliente({ renovar: async () => false })
    cliente.ligar()
    ultimo().abrir()

    ultimo().cair(FECHAMENTO.naoAutenticado)
    await vi.runAllTimersAsync()

    expect(SocketFalso.criados).toHaveLength(1)
    expect(cliente.estado).toBe('desligado')
  })

  it('sem token, nem tenta conectar', () => {
    const cliente = novoCliente({ token: () => null })
    cliente.ligar()

    expect(SocketFalso.criados).toHaveLength(0)
    expect(cliente.estado).toBe('desligado')
  })

  it('desligar não reconecta', () => {
    const cliente = novoCliente()
    cliente.ligar()
    conectar()

    cliente.desligar()
    vi.advanceTimersByTime(60_000)

    expect(SocketFalso.criados).toHaveLength(1)
    expect(cliente.estado).toBe('desligado')
  })
})
