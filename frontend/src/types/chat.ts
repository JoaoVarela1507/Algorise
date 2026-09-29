export type AutorMensagem = 'usuario' | 'assistente'

export interface Mensagem {
  id: string
  autor: AutorMensagem
  conteudo: string
  /** Timestamp em ms (serializa direto no localStorage). */
  criadaEm: number
  /** Nome do arquivo anexado, se houver. */
  anexo?: string
  erro?: boolean
}

export interface Conversa {
  id: string
  titulo: string
  mensagens: Mensagem[]
  atualizadaEm: number
  grupoId?: string
}

export interface GrupoConversas {
  id: string
  nome: string
}

/** Quanto o assistente deve se aprofundar na resposta. */
export type ModoResposta = 'rapido' | 'medio' | 'detalhado'
