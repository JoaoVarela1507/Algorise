import { useEffect, useState } from 'react'
import { motion, useReducedMotionConfig } from 'framer-motion'
import { AlertCircle, RotateCcw, Scissors } from 'lucide-react'
import { toast } from '@/components/ui/toaster'
import { cn } from '@/lib/utils'
import { baixarAnexo } from '@/services/chat'
import type { Mensagem } from '@/types/chat'
import { ChipAnexo } from './ChipAnexo'
import { Markdown } from './Markdown'
import mascotePolvo from '@/assets/images/mascote-polvo.png'

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

/**
 * `incompleta`: a IA parou no meio (queda, limite, "Parar resposta"). Fica só
 * na tela (a API grava `incompleta`, mas a tela também a usa para a resposta em curso).
 */
export type MensagemDoChat = Mensagem & {
  incompleta?: boolean
  /** Repetir a pergunta não adianta (ex.: a conversa sumiu do servidor). */
  semRetentativa?: boolean
}

export function MensagemChat({
  mensagem,
  animarDigitacao = false,
  aoTentarDeNovo,
}: {
  mensagem: MensagemDoChat
  animarDigitacao?: boolean
  /** Quando existe, mostra "Tentar de novo" (só na última resposta com problema). */
  aoTentarDeNovo?: () => void
}) {
  const texto = useRevelar(mensagem.conteudo, animarDigitacao)

  if (mensagem.autor === 'usuario') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        className="flex flex-col items-end gap-1"
      >
        {mensagem.anexos?.map((anexo) => (
          <ChipAnexo
            key={anexo.id}
            anexo={anexo}
            aoBaixar={() =>
              baixarAnexo(anexo).catch(() => toast.error('Não foi possível baixar o anexo.'))
            }
          />
        ))}
        <div className="min-w-0 max-w-[75%] rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-primary-foreground shadow-sm">
          <Markdown texto={mensagem.conteudo} />
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
          'min-w-0 max-w-[80%] rounded-2xl rounded-tl-md border bg-card px-4 py-3 text-foreground shadow-sm',
          mensagem.erro ? 'border-destructive/50' : 'border-border',
        )}
      >
        {mensagem.erro && (
          <span className="mb-1 flex items-center gap-1.5 text-sm font-bold text-destructive">
            <AlertCircle className="size-4" aria-hidden />
            Erro
          </span>
        )}
        <Markdown texto={texto} />
        {mensagem.incompleta && !mensagem.erro && (
          <p className="mt-2 flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
            <Scissors className="size-3.5" aria-hidden />
            Resposta interrompida: pode estar cortada.
          </p>
        )}
        {aoTentarDeNovo && (
          <button
            type="button"
            onClick={aoTentarDeNovo}
            className="mt-2 flex min-h-8 items-center gap-1.5 rounded-md border border-border px-3 text-sm font-semibold text-primary transition-colors hover:bg-accent/60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
          >
            <RotateCcw className="size-3.5" aria-hidden />
            Tentar de novo
          </button>
        )}
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
