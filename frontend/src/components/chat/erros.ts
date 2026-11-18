import { ApiError } from '@/services/api'

// Mensagens por código do servidor (ver ERROS_DO_CHAT em chatAoVivo.ts). O
// texto da API também é em português, mas pode mudar sem aviso: aqui o tom
// fica sob nosso controle e sempre diz o que a pessoa pode fazer.
const POR_CODIGO: Record<string, string> = {
  rate_limit: 'Você mandou muitas mensagens em pouco tempo. Espere um minutinho e tente de novo.',
  ia_indisponivel: 'O tutor está fora do ar agora. Tente de novo em alguns instantes.',
  chat_ocupado:
    'O tutor ainda está respondendo à mensagem anterior. Espere ele terminar e tente de novo.',
  conversa_nao_encontrada:
    'Não encontrei essa conversa no servidor. Comece um novo bate-papo para continuar.',
  erro_interno: 'Algo deu errado do nosso lado. Tente de novo em instantes.',
}

const POR_STATUS: Record<number, string> = {
  0: 'Sem conexão com o servidor. Confira sua internet e tente de novo.',
  408: 'A resposta demorou demais. Tente de novo.',
  429: POR_CODIGO.rate_limit,
  502: POR_CODIGO.ia_indisponivel,
  503: POR_CODIGO.ia_indisponivel,
  504: 'A resposta demorou demais. Tente de novo.',
}

const GENERICA = 'Não consegui responder agora. Tente de novo em instantes.'

/** Códigos em que repetir a mesma pergunta não resolve (a conversa sumiu). */
const SEM_RETENTATIVA = new Set(['conversa_nao_encontrada'])

export function mensagemDeErro(erro: unknown): string {
  if (!(erro instanceof ApiError)) return GENERICA
  if (erro.code && POR_CODIGO[erro.code]) return POR_CODIGO[erro.code]
  if (POR_STATUS[erro.status]) return POR_STATUS[erro.status]
  // Erro com texto do servidor (ex.: validação) é mais útil que o genérico.
  return erro.status >= 400 && erro.status < 500 && erro.message ? erro.message : GENERICA
}

export function podeTentarDeNovo(erro: unknown): boolean {
  return !(erro instanceof ApiError && erro.code && SEM_RETENTATIVA.has(erro.code))
}
