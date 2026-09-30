import { Fragment, useEffect, useState, type ReactNode } from 'react'
import { motion, useReducedMotionConfig } from 'framer-motion'
import { AlertCircle, Paperclip } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Mensagem } from '@/types/chat'
import mascotePolvo from '@/assets/images/mascote-polvo.png'

/** Negrito, itálico e `código` dentro de uma linha. */
function formatarLinha(texto: string): ReactNode[] {
  return texto.split(/(\*\*[^*]+\*\*|`[^`]+`|_[^_]+_)/g).map((parte, i) => {
    if (parte.startsWith('**') && parte.endsWith('**') && parte.length > 4) {
      return <strong key={i}>{parte.slice(2, -2)}</strong>
    }
    if (parte.startsWith('`') && parte.endsWith('`') && parte.length > 2) {
      return (
        <code key={i} className="rounded bg-muted px-1.5 py-0.5 font-mono text-[0.9em]">
          {parte.slice(1, -1)}
        </code>
      )
    }
    if (parte.startsWith('_') && parte.endsWith('_') && parte.length > 2) {
      return <em key={i}>{parte.slice(1, -1)}</em>
    }
    return <Fragment key={i}>{parte}</Fragment>
  })
}

/**
 * Renderização mínima de markdown (blocos de código e ênfase). Quando o
 * chatbot real entrar, dá pra trocar por uma lib como react-markdown.
 */
function ConteudoMensagem({ texto }: { texto: string }) {
  const blocos = texto.split(/```(\w*)\n?([\s\S]*?)(?:```|$)/g)
  const elementos: ReactNode[] = []

  for (let i = 0; i < blocos.length; i += 3) {
    const trecho = blocos[i]
    if (trecho?.trim()) {
      elementos.push(
        <p key={`t${i}`} className="whitespace-pre-wrap">
          {formatarLinha(trecho.trim())}
        </p>,
      )
    }
    const codigo = blocos[i + 2]
    if (codigo !== undefined) {
      elementos.push(
        <pre
          key={`c${i}`}
          className="overflow-x-auto rounded-md bg-foreground/90 p-3 font-mono text-sm text-background"
        >
          <code>{codigo.replace(/\n$/, '')}</code>
        </pre>,
      )
    }
  }

  return <div className="flex flex-col gap-3">{elementos}</div>
}

/** Revela o texto aos poucos, imitando o streaming de um chatbot. */
function useRevelar(texto: string, ativo: boolean) {
  const reduzirMovimento = useReducedMotionConfig()
  const animar = ativo && !reduzirMovimento
  const [tamanho, setTamanho] = useState(animar ? 0 : texto.length)

  useEffect(() => {
    if (!animar) {
      setTamanho(texto.length)
      return
    }
    let atual = 0
    const timer = setInterval(() => {
      atual += 3
      setTamanho(Math.min(atual, texto.length))
      if (atual >= texto.length) clearInterval(timer)
    }, 16)
    return () => clearInterval(timer)
  }, [texto, animar])

  return texto.slice(0, tamanho)
}

export function AvatarAssistente({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        'flex size-9 shrink-0 items-center justify-center rounded-full bg-accent/60',
        className,
      )}
    >
      <img src={mascotePolvo} alt="" className="size-7 object-contain" />
    </span>
  )
}

export function MensagemChat({
  mensagem,
  animarDigitacao = false,
}: {
  mensagem: Mensagem
  animarDigitacao?: boolean
}) {
  const texto = useRevelar(mensagem.conteudo, animarDigitacao)

  if (mensagem.autor === 'usuario') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        className="flex flex-col items-end gap-1"
      >
        {mensagem.anexo && (
          <span className="flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1 text-xs font-semibold text-muted-foreground">
            <Paperclip className="size-3.5" aria-hidden />
            {mensagem.anexo}
          </span>
        )}
        <div className="max-w-[75%] rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-primary-foreground shadow-sm">
          <ConteudoMensagem texto={mensagem.conteudo} />
        </div>
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-start gap-3"
    >
      <AvatarAssistente />
      <div
        className={cn(
          'max-w-[80%] rounded-2xl rounded-tl-md border bg-card px-4 py-3 text-foreground shadow-sm',
          mensagem.erro ? 'border-destructive/50' : 'border-border',
        )}
      >
        {mensagem.erro && (
          <span className="mb-1 flex items-center gap-1.5 text-sm font-bold text-destructive">
            <AlertCircle className="size-4" aria-hidden />
            Erro
          </span>
        )}
        <ConteudoMensagem texto={texto} />
      </div>
    </motion.div>
  )
}

export function IndicadorDigitando() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="flex items-center gap-3"
      role="status"
      aria-label="O Algorise está digitando"
    >
      <AvatarAssistente />
      <div className="flex gap-1.5 rounded-2xl rounded-tl-md border border-border bg-card px-4 py-4 shadow-sm">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="size-2 rounded-full bg-primary"
            animate={{ y: [0, -5, 0], opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.15 }}
          />
        ))}
      </div>
    </motion.div>
  )
}
