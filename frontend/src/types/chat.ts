import type { AnexoDoChat } from '@/services/chat'

export type AutorMensagem = 'usuario' | 'assistente'

/** Uma mensagem na tela: vinda da API ou ainda local (pergunta enviada, erro). */
export interface Mensagem {
  id: string
  autor: AutorMensagem
  conteudo: string
  /** Timestamp em ms. */
  criadaEm: number
  anexos?: AnexoDoChat[]
  erro?: boolean
}

/** Quanto o assistente deve se aprofundar na resposta. */
export type ModoResposta = 'rapido' | 'medio' | 'detalhado'
