import { ApiError } from '@/services/api'
import { perguntarAoTutor, type PedidoAoTutor, type RespostaDoTutor } from '@/services/chat'
import type { ClienteTempoReal } from '@/services/tempoReal'

/**
 * Pergunta ao tutor pelo WebSocket (#36), com o SSE de fallback.
 *
 * Com a conexão de tempo real aberta, a pergunta vai como `chat.mensagem.enviar`
 * e a resposta chega no canal `chat:{conversa_id}`. Com ela fechada (rede que
 * bloqueia WebSocket, servidor reconectando), cai no `POST /chat/mensagens` em
 * SSE, que entrega a mesma resposta em pedaços. Nos dois, `parar` interrompe, e
 * o que já foi gerado fica gravado como incompleto.
 */

export interface PerguntaAoVivo {
  resposta: Promise<RespostaDoTutor>
  parar: () => void
}

// Erros do servidor que respondem a uma pergunta, e o status HTTP equivalente.
const ERROS_DO_CHAT: Record<string, number> = {
  conversa_nao_encontrada: 404,
  chat_ocupado: 409,
  rate_limit: 429,
  ia_indisponivel: 503,
  erro_interno: 500,
}

export function perguntar(
  cliente: ClienteTempoReal,
  pedido: PedidoAoTutor,
  aoReceber?: (parcial: string) => void,
): PerguntaAoVivo {
  if (cliente.estado !== 'aberto') {
    const controle = new AbortController()
    return {
      resposta: perguntarAoTutor(pedido, aoReceber, controle.signal),
      parar: () => controle.abort(),
    }
  }

  let conversaId = pedido.conversaId ?? null
  let pararPedido = false
  const pedirParada = (id: number) => cliente.enviar({ tipo: 'chat.parar', conversa_id: id })

  const resposta = new Promise<RespostaDoTutor>((resolver, rejeitar) => {
    let titulo = ''
    let texto = ''
    let soltarCanal: (() => void) | null = null
    const limpar: (() => void)[] = []
    const terminar = (fim: () => void) => {
      limpar.forEach((soltar) => soltar())
      soltarCanal?.()
      fim()
    }
    const devolver = (incompleta: boolean) =>
      terminar(() => resolver({ conversaId: conversaId ?? 0, titulo, resposta: texto, incompleta }))

    limpar.push(
      cliente.ouvirServidor((mensagem) => {
        if (mensagem.tipo === 'erro') {
          const status = ERROS_DO_CHAT[mensagem.code]
          if (status) {
            terminar(() => rejeitar(new ApiError(status, mensagem.message, mensagem.code)))
          }
          return
        }
        if (mensagem.tipo !== 'evento' || !mensagem.canal.startsWith('chat:')) return
        const id = Number(mensagem.canal.slice('chat:'.length))

        if (conversaId === null && mensagem.evento === 'chat.conversa') {
          // Conversa nova: o servidor já pôs esta aba no canal dela. A
          // inscrição daqui é para ela voltar sozinha numa reconexão.
          conversaId = id
          soltarCanal = cliente.assinar(mensagem.canal, () => undefined)
          if (pararPedido) pedirParada(id)
        }
        if (id !== conversaId) return

        const payload = mensagem.payload ?? {}
        switch (mensagem.evento) {
          case 'chat.conversa':
            titulo = String(payload.titulo ?? '')
            break
          case 'chat.token':
            texto += String(payload.texto ?? '')
            aoReceber?.(texto)
            break
          case 'chat.fim':
            devolver(false)
            break
          case 'chat.parado':
          case 'chat.erro':
            devolver(true)
            break
        }
      }),
      // A conexão caiu no meio: o servidor grava o parcial; aqui ele volta
      // incompleto, em vez de esperar um fim que não vem.
      cliente.ouvirEstado((estado) => {
        if (estado !== 'aberto') devolver(true)
      }),
    )

    if (conversaId !== null) soltarCanal = cliente.assinar(`chat:${conversaId}`, () => undefined)
    cliente.enviar({
      tipo: 'chat.mensagem.enviar',
      conteudo: pedido.conteudo,
      conversa_id: conversaId,
      modo: pedido.modo,
    })
  })

  return {
    resposta,
    parar: () => {
      if (conversaId !== null) pedirParada(conversaId)
      else pararPedido = true
    },
  }
}
