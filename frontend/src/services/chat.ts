import { apiResposta } from '@/services/api'
import type { ModoResposta } from '@/types/chat'

/**
 * Onde a lista de conversas fica neste navegador. As mensagens também ficam
 * gravadas na API, que é de onde o tutor tira o contexto; listar, buscar e
 * agrupar pela API é a #33, e até lá a lista da tela continua aqui.
 */
export const CHAVE_HISTORICO_CHAT = 'algorise:chat'

/** Apaga as conversas e os grupos. Grava vazio para os exemplos não voltarem. */
export function limparHistoricoChat() {
  try {
    localStorage.setItem(CHAVE_HISTORICO_CHAT, JSON.stringify({ conversas: [], grupos: [] }))
  } catch {
    // Sem armazenamento não há histórico salvo para apagar.
  }
}

export const modosResposta: { valor: ModoResposta; rotulo: string }[] = [
  { valor: 'rapido', rotulo: 'Rápido' },
  { valor: 'medio', rotulo: 'Médio' },
  { valor: 'detalhado', rotulo: 'Detalhado' },
]

export interface PedidoAoTutor {
  /** Conversa da API em que a mensagem entra. Sem ele, a API abre uma nova. */
  conversaId?: number
  conteudo: string
  modo: ModoResposta
}

export interface RespostaDoTutor {
  conversaId: number
  titulo: string
  resposta: string
  /** A IA parou no meio: `resposta` é o que deu tempo de gerar. */
  incompleta: boolean
}

export interface EventoDoChat {
  evento: string
  dados: Record<string, unknown>
}

/**
 * Manda a pergunta e lê a resposta do tutor em streaming (`text/event-stream`).
 *
 * `aoReceber` é chamado a cada pedaço, com o texto acumulado, para quem quiser
 * mostrar a resposta enquanto ela chega. Erros antes do streaming (limite de
 * mensagens, IA fora do ar) sobem como `ApiError`, com a mensagem da API.
 */
export async function perguntarAoTutor(
  { conversaId, conteudo, modo }: PedidoAoTutor,
  aoReceber?: (parcial: string) => void,
): Promise<RespostaDoTutor> {
  const resposta = await apiResposta('/chat/mensagens', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify({ conversa_id: conversaId ?? null, conteudo, modo }),
  })

  let conversa = { conversaId: conversaId ?? 0, titulo: '' }
  let texto = ''
  let incompleta = true

  for await (const { evento, dados } of lerEventos(resposta.body)) {
    if (evento === 'chat.conversa') {
      conversa = { conversaId: Number(dados.conversa_id), titulo: String(dados.titulo) }
    } else if (evento === 'chat.token') {
      texto += String(dados.texto)
      aoReceber?.(texto)
    } else if (evento === 'chat.fim') {
      incompleta = false
    }
    // `chat.erro` não precisa de nada: sem o `chat.fim`, a resposta fica
    // incompleta, que é o que ele quer dizer.
  }

  return { ...conversa, resposta: texto, incompleta }
}

/** Os eventos de um corpo SSE, na ordem, conforme vão chegando. */
export async function* lerEventos(
  corpo: ReadableStream<Uint8Array> | null,
): AsyncGenerator<EventoDoChat> {
  if (!corpo) return
  const leitor = corpo.getReader()
  // `stream: true` segura o byte de um "ç" que chegou partido entre dois
  // pedaços da rede, em vez de virar "�".
  const decodificador = new TextDecoder()
  let acumulado = ''

  try {
    for (;;) {
      const { value, done } = await leitor.read()
      acumulado += decodificador.decode(value, { stream: !done })
      // Um evento termina numa linha em branco; o que sobrar é um evento que
      // ainda está chegando, cortado no meio pela rede.
      const blocos = acumulado.split('\n\n')
      acumulado = done ? '' : (blocos.pop() ?? '')
      for (const bloco of blocos) {
        const evento = lerBloco(bloco)
        if (evento) yield evento
      }
      if (done) return
    }
  } finally {
    leitor.releaseLock()
  }
}

function lerBloco(bloco: string): EventoDoChat | null {
  let evento = 'message'
  const dados: string[] = []
  for (const linha of bloco.split('\n')) {
    if (linha.startsWith('event:')) evento = linha.slice(6).trim()
    else if (linha.startsWith('data:')) dados.push(linha.slice(5).trimStart())
  }
  if (dados.length === 0) return null
  try {
    return { evento, dados: JSON.parse(dados.join('\n')) as Record<string, unknown> }
  } catch {
    return null
  }
}
