import type { components } from '@/types/api'
import { API_V1 } from '@/services/api'

/**
 * Cliente do WebSocket da API (`WS /api/v1/ws`, #35).
 *
 * Uma conexão por aba, multiplexada em canais (`chat:{id}`, `ranking:{id}`,
 * `notificacoes:{id}`). O contrato das mensagens vem gerado do OpenAPI.
 *
 * - **Autenticação:** o token vai no primeiro frame, nunca na URL. Fechou com
 *   4401 (token vencido), a sessão é renovada antes de reconectar.
 * - **Reconexão:** espera exponencial com jitter, até `atrasoMaximo`. Ao voltar,
 *   as inscrições são refeitas sozinhas.
 * - **Fila offline:** o que for enviado com a conexão fechada sai quando ela
 *   voltar, até `TAMANHO_DA_FILA` mensagens.
 */

export type MensagemDoCliente = components['schemas']['MensagemDoCliente']
export type MensagemDoServidor = components['schemas']['MensagemDoServidor']
export type Evento = components['schemas']['Evento']
export type EstadoConexao = 'desligado' | 'conectando' | 'aberto' | 'reconectando'

export const URL_DO_WS = `${API_V1.replace(/^http/, 'ws')}/ws`
export const TAMANHO_DA_FILA = 100

/** Códigos de fechamento do servidor (ver `app/api/v1/tempo_real.py`). */
export const FECHAMENTO = {
  naoAutenticado: 4401,
  conexaoMorta: 4408,
  conexoesDemais: 4429,
} as const

type Ouvinte = (evento: Evento) => void

interface SocketMinimo {
  readyState: number
  send: (dados: string) => void
  close: (codigo?: number) => void
  onopen: ((ev: Event) => void) | null
  onmessage: ((ev: MessageEvent) => void) | null
  onclose: ((ev: CloseEvent) => void) | null
  onerror: ((ev: Event) => void) | null
}

export interface OpcoesTempoReal {
  /** O access token atual; `null` não conecta. */
  token: () => string | null
  /** Renova a sessão quando o servidor recusa o token. */
  renovar: () => Promise<boolean>
  aoMudarEstado?: (estado: EstadoConexao) => void
  aoErro?: (erro: { code: string; message: string }) => void
  url?: string
  criarSocket?: (url: string) => SocketMinimo
  atrasoBase?: number
  atrasoMaximo?: number
  aleatorio?: () => number
}

const ABERTO = 1

export class ClienteTempoReal {
  private socket: SocketMinimo | null = null
  private autenticado = false
  private ligado = false
  private tentativas = 0
  private espera: ReturnType<typeof setTimeout> | null = null
  private readonly canais = new Map<string, Set<Ouvinte>>()
  private readonly fila: MensagemDoCliente[] = []
  private readonly doServidor = new Set<(mensagem: MensagemDoServidor) => void>()
  private readonly deEstado = new Set<(estado: EstadoConexao) => void>()
  estado: EstadoConexao = 'desligado'

  constructor(private readonly opcoes: OpcoesTempoReal) {}

  /** Liga e mantém ligado até `desligar`. */
  ligar() {
    if (this.ligado) return
    this.ligado = true
    this.abrir()
  }

  desligar() {
    this.ligado = false
    this.limparEspera()
    this.tentativas = 0
    this.fila.length = 0
    const socket = this.socket
    this.socket = null
    this.autenticado = false
    if (socket) {
      socket.onclose = null
      socket.close(1000)
    }
    this.mudarEstado('desligado')
  }

  /** Ouve um canal; devolve a função que para de ouvir. */
  assinar(canal: string, ouvinte: Ouvinte): () => void {
    let ouvintes = this.canais.get(canal)
    if (!ouvintes) {
      ouvintes = new Set()
      this.canais.set(canal, ouvintes)
      if (this.autenticado) this.mandar({ tipo: 'inscrever', canal })
    }
    ouvintes.add(ouvinte)

    return () => {
      const atuais = this.canais.get(canal)
      if (!atuais) return
      atuais.delete(ouvinte)
      if (atuais.size === 0) {
        this.canais.delete(canal)
        if (this.autenticado) this.mandar({ tipo: 'cancelar', canal })
      }
    }
  }

  /**
   * Ouve toda mensagem do servidor, de qualquer canal, e os erros. É o que o
   * chat usa para pegar a conversa nova, cujo canal ele ainda não conhece.
   */
  ouvirServidor(ouvinte: (mensagem: MensagemDoServidor) => void): () => void {
    this.doServidor.add(ouvinte)
    return () => this.doServidor.delete(ouvinte)
  }

  /** Ouve as mudanças de estado da conexão. */
  ouvirEstado(ouvinte: (estado: EstadoConexao) => void): () => void {
    this.deEstado.add(ouvinte)
    return () => this.deEstado.delete(ouvinte)
  }

  /** Envia agora, ou guarda para quando a conexão voltar. */
  enviar(mensagem: MensagemDoCliente) {
    if (this.autenticado) {
      this.mandar(mensagem)
      return
    }
    if (this.fila.length >= TAMANHO_DA_FILA) this.fila.shift()
    this.fila.push(mensagem)
  }

  private abrir() {
    const token = this.opcoes.token()
    if (!token) {
      // Sem sessão com token (o login de teste, por exemplo): fica desligado
      // até o próximo `ligar`, em vez de tentar à toa.
      this.ligado = false
      this.mudarEstado('desligado')
      return
    }
    this.mudarEstado(this.tentativas === 0 ? 'conectando' : 'reconectando')
    const criar = this.opcoes.criarSocket ?? ((url: string) => new WebSocket(url))
    const socket = criar(this.opcoes.url ?? URL_DO_WS)
    this.socket = socket

    socket.onopen = () => socket.send(JSON.stringify({ tipo: 'autenticar', token }))
    socket.onmessage = (ev) => this.receber(ev.data)
    socket.onclose = (ev) => void this.aoFechar(ev.code)
    // O `onclose` vem logo depois e cuida da reconexão.
    socket.onerror = () => undefined
  }

  private receber(dados: unknown) {
    let mensagem: MensagemDoServidor
    try {
      mensagem = JSON.parse(String(dados)) as MensagemDoServidor
    } catch {
      return
    }
    this.doServidor.forEach((ouvinte) => ouvinte(mensagem))
    switch (mensagem.tipo) {
      case 'autenticado':
        if (!this.autenticado) this.aoAutenticar()
        break
      case 'evento':
        this.canais.get(mensagem.canal)?.forEach((ouvinte) => ouvinte(mensagem))
        break
      case 'ping':
        this.mandar({ tipo: 'pong' })
        break
      case 'erro':
        this.opcoes.aoErro?.({ code: mensagem.code, message: mensagem.message })
        break
    }
  }

  private aoAutenticar() {
    this.autenticado = true
    this.tentativas = 0
    this.mudarEstado('aberto')
    for (const canal of this.canais.keys()) this.mandar({ tipo: 'inscrever', canal })
    for (const mensagem of this.fila.splice(0)) this.mandar(mensagem)
  }

  private async aoFechar(codigo: number) {
    this.socket = null
    this.autenticado = false
    if (!this.ligado) return
    if (codigo === FECHAMENTO.naoAutenticado && !(await this.opcoes.renovar())) {
      // A sessão acabou: sem token novo, não adianta insistir.
      this.desligar()
      return
    }
    this.agendar()
  }

  private agendar() {
    this.limparEspera()
    if (!this.ligado) return
    const { atrasoBase = 500, atrasoMaximo = 30_000, aleatorio = Math.random } = this.opcoes
    const teto = Math.min(atrasoMaximo, atrasoBase * 2 ** this.tentativas)
    // Jitter: metade fixa e metade sorteada, para as abas não voltarem juntas.
    const atraso = teto / 2 + (teto / 2) * aleatorio()
    this.tentativas += 1
    this.mudarEstado('reconectando')
    this.espera = setTimeout(() => {
      this.espera = null
      this.abrir()
    }, atraso)
  }

  private mandar(mensagem: MensagemDoCliente) {
    if (this.socket?.readyState === ABERTO) this.socket.send(JSON.stringify(mensagem))
  }

  private limparEspera() {
    if (this.espera !== null) clearTimeout(this.espera)
    this.espera = null
  }

  private mudarEstado(estado: EstadoConexao) {
    if (this.estado === estado) return
    this.estado = estado
    this.opcoes.aoMudarEstado?.(estado)
    this.deEstado.forEach((ouvinte) => ouvinte(estado))
  }
}
