import type { Mensagem, ModoResposta } from '@/types/chat'

/** Onde o histórico do chat fica enquanto não há backend (só neste navegador). */
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

export interface OpcoesEnvio {
  modo: ModoResposta
  anexo?: string
}

/**
 * Ponto único de integração com o chatbot. Por enquanto devolve respostas de
 * exemplo com um atraso simulado; quando o backend existir, troque o corpo
 * por algo como `apiPost<{ resposta: string }>('/chat', { historico, ...opcoes })`.
 * A tela não precisa mudar.
 */
export async function enviarMensagem(historico: Mensagem[], opcoes: OpcoesEnvio): Promise<string> {
  const pergunta = historico[historico.length - 1]?.conteudo ?? ''
  await new Promise((resolve) => setTimeout(resolve, 800 + Math.random() * 700))
  return respostaDeExemplo(pergunta, opcoes)
}

function respostaDeExemplo(pergunta: string, { modo, anexo }: OpcoesEnvio) {
  const texto = pergunta.toLowerCase()
  const partes: string[] = []

  if (anexo) {
    partes.push(`Recebi o arquivo **${anexo}**. Quando eu estiver conectado, vou conseguir lê-lo.`)
  }

  if (texto.includes('recurs')) {
    partes.push(
      'Recursão é quando uma função chama a si mesma para resolver um problema menor do mesmo tipo. Um exemplo clássico é o fatorial:',
      '```python\ndef fatorial(n):\n    if n <= 1:  # caso base\n        return 1\n    return n * fatorial(n - 1)\n```',
      'Todo algoritmo recursivo precisa de um **caso base**, senão ele nunca para.',
    )
  } else if (texto.includes('tcp') || texto.includes('udp')) {
    partes.push(
      'O TCP é orientado à conexão: garante entrega e ordem dos pacotes, ideal para páginas web e arquivos. O UDP não garante nada disso, mas é mais leve e rápido, ótimo para jogos e chamadas de vídeo.',
    )
  } else if (texto.includes('ementa')) {
    partes.push(
      'Sua ementa define a ordem das trilhas guiadas. Posso te explicar qualquer disciplina dela, é só me dizer qual! 📚',
    )
  } else {
    partes.push(
      'Ainda estou em treinamento! 🐙 Em breve vou responder suas dúvidas de programação com base na ementa do seu curso.',
      `Você perguntou: “${pergunta}”`,
    )
  }

  if (modo === 'detalhado') {
    partes.push('_(No modo detalhado, eu trarei exemplos e exercícios extras.)_')
  }

  return partes.join('\n\n')
}
