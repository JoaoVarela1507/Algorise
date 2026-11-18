import { apiFetch, apiGet, apiPatch, apiPost, apiResposta } from '@/services/api'
import type { components } from '@/types/api'
import type { ModoResposta } from '@/types/chat'

export type ConversaResumo = components['schemas']['ConversaResumo']
export type GrupoDeConversas = components['schemas']['Grupo']
export type AnexoDoChat = components['schemas']['Anexo']
export type MensagemApi = components['schemas']['Mensagem']
type PaginaDeConversas = components['schemas']['Pagina_ConversaResumo_']
type PaginaDeMensagens = components['schemas']['Pagina_Mensagem_']

/** O teto de itens por página da API: o histórico vem em fatias desse tamanho. */
export const TAMANHO_PAGINA_CONVERSAS = 50
const TAMANHO_PAGINA_MENSAGENS = 100

export function listarConversas({
  busca,
  pagina = 1,
}: { busca?: string; pagina?: number } = {}): Promise<PaginaDeConversas> {
  const parametros = new URLSearchParams({
    pagina: String(pagina),
    tamanho_pagina: String(TAMANHO_PAGINA_CONVERSAS),
  })
  if (busca) parametros.set('busca', busca)
  return apiGet<PaginaDeConversas>(`/chat/conversas?${parametros}`)
}

/**
 * Todas as mensagens da conversa, na ordem. O tutor lembra da conversa inteira,
 * então a tela também precisa dela inteira, e não só da primeira página.
 */
export async function listarMensagens(conversaId: number): Promise<MensagemApi[]> {
  const mensagens: MensagemApi[] = []
  for (let pagina = 1; ; pagina++) {
    const resposta = await apiGet<PaginaDeMensagens>(
      `/chat/conversas/${conversaId}/mensagens?pagina=${pagina}&tamanho_pagina=${TAMANHO_PAGINA_MENSAGENS}`,
    )
    mensagens.push(...resposta.itens)
    if (pagina >= resposta.total_paginas) return mensagens
  }
}

export function editarConversa(
  id: number,
  dados: { titulo?: string; arquivada?: boolean; grupo_id?: number | null },
): Promise<ConversaResumo> {
  return apiPatch<ConversaResumo>(`/chat/conversas/${id}`, dados)
}

export function apagarConversa(id: number): Promise<void> {
  return apiFetch<void>(`/chat/conversas/${id}`, { method: 'DELETE' })
}

/** Apaga todas as conversas do aluno (os grupos ficam vazios). */
export async function apagarHistoricoChat(): Promise<void> {
  // Sempre a primeira página: ao apagar, a seguinte passa a ser a primeira.
  for (;;) {
    const { itens } = await listarConversas()
    if (itens.length === 0) return
    await Promise.all(itens.map((conversa) => apagarConversa(conversa.id)))
  }
}

export function listarGrupos(): Promise<GrupoDeConversas[]> {
  return apiGet<GrupoDeConversas[]>('/chat/grupos')
}

export function criarGrupo(nome: string, conversaIds: number[]): Promise<GrupoDeConversas> {
  return apiPost<GrupoDeConversas>('/chat/grupos', { nome, conversa_ids: conversaIds })
}

/** `conversaIds` é a lista inteira do grupo: quem não está nela sai dele. */
export function editarGrupo(
  id: number,
  dados: { nome?: string; conversa_ids?: number[] },
): Promise<GrupoDeConversas> {
  return apiPatch<GrupoDeConversas>(`/chat/grupos/${id}`, dados)
}

export function apagarGrupo(id: number): Promise<void> {
  return apiFetch<void>(`/chat/grupos/${id}`, { method: 'DELETE' })
}

// --- anexos ---------------------------------------------------------------------------

/** Igual ao backend (`chat_anexo_tamanho_maximo`): ele continua sendo quem decide. */
export const TAMANHO_MAXIMO_ANEXO = 2 * 1024 * 1024
/** Igual ao backend (`chat_anexos_por_mensagem`). */
export const ANEXOS_POR_MENSAGEM = 3

// O backend reconhece o tipo pelo conteúdo; a extensão aqui só evita subir à toa
// um arquivo que ele recusaria.
const EXTENSOES_ACEITAS = [
  '.txt', '.md', '.csv', '.json', '.py', '.ipynb', '.c', '.h', '.cpp', '.java', '.js', '.ts',
  '.html', '.css', '.sql', '.sh', '.yml', '.yaml', '.pdf', '.png', '.jpg', '.jpeg', '.webp',
] // prettier-ignore

/** Valor do `accept` do input de arquivo. */
export const ACCEPT_ANEXOS = EXTENSOES_ACEITAS.join(',')

/** A mensagem de erro (em português) se o arquivo não pode ser anexado; `null` se pode. */
export function validarAnexo(arquivo: File): string | null {
  const nome = arquivo.name.toLowerCase()
  if (!EXTENSOES_ACEITAS.some((extensao) => nome.endsWith(extensao))) {
    return 'Tipo de arquivo não aceito. Anexe texto, código, PDF ou imagem (PNG, JPEG ou WebP).'
  }
  if (arquivo.size > TAMANHO_MAXIMO_ANEXO) {
    return `O anexo pode ter até ${TAMANHO_MAXIMO_ANEXO / (1024 * 1024)} MB.`
  }
  if (arquivo.size === 0) return 'O arquivo está vazio.'
  return null
}

export function enviarAnexo(arquivo: File): Promise<AnexoDoChat> {
  const formulario = new FormData()
  formulario.append('arquivo', arquivo)
  // Sem `Content-Type`: o navegador põe o multipart com o boundary certo.
  return apiFetch<AnexoDoChat>('/chat/anexos', { method: 'POST', body: formulario })
}

export function apagarAnexo(id: number): Promise<void> {
  return apiFetch<void>(`/chat/anexos/${id}`, { method: 'DELETE' })
}

/** A API só serve o anexo com token, então o download passa pelo `fetch`. */
export async function baixarAnexo(anexo: AnexoDoChat): Promise<void> {
  const resposta = await apiResposta(`/chat/anexos/${anexo.id}`)
  const url = URL.createObjectURL(await resposta.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = anexo.nome
  link.click()
  URL.revokeObjectURL(url)
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
  /** Anexos já enviados em `POST /chat/anexos`. */
  anexoIds?: number[]
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
  { conversaId, conteudo, modo, anexoIds = [] }: PedidoAoTutor,
  aoReceber?: (parcial: string) => void,
  sinal?: AbortSignal,
): Promise<RespostaDoTutor> {
  const resposta = await apiResposta('/chat/mensagens', {
    method: 'POST',
    signal: sinal,
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify({ conversa_id: conversaId ?? null, conteudo, modo, anexo_ids: anexoIds }),
  })

  let conversa = { conversaId: conversaId ?? 0, titulo: '' }
  let texto = ''
  let incompleta = true

  try {
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
  } catch (erro) {
    // O aluno parou: o servidor grava o parcial, e aqui ele volta incompleto.
    if (!sinal?.aborted) throw erro
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
