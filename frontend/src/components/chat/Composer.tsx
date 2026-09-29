import { useId, useLayoutEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowUp, Mic, Paperclip, Plus, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useDitado } from '@/hooks/useDitado'
import { cn } from '@/lib/utils'
import { modosResposta } from '@/services/chat'
import type { ModoResposta } from '@/types/chat'

const ALTURA_MAXIMA = 200

export function Composer({
  onEnviar,
  ocupado,
  modo,
  onModoChange,
  autoFocus,
  className,
}: {
  onEnviar: (texto: string, anexo?: string) => void
  ocupado: boolean
  modo: ModoResposta
  onModoChange: (modo: ModoResposta) => void
  autoFocus?: boolean
  className?: string
}) {
  const [texto, setTexto] = useState('')
  const [anexo, setAnexo] = useState<File | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const arquivoId = useId()
  const { ouvindo, suportado, alternar } = useDitado((falado) =>
    setTexto((atual) => (atual.trim() ? `${atual.trimEnd()} ${falado.trim()}` : falado.trim())),
  )

  // Cresce com o texto até um limite; depois disso rola por dentro.
  useLayoutEffect(() => {
    const campo = textareaRef.current
    if (!campo) return
    campo.style.height = 'auto'
    campo.style.height = `${Math.min(campo.scrollHeight, ALTURA_MAXIMA)}px`
  }, [texto])

  const podeEnviar = texto.trim().length > 0 && !ocupado

  function enviar() {
    if (!podeEnviar) return
    onEnviar(texto.trim(), anexo?.name)
    setTexto('')
    setAnexo(null)
    textareaRef.current?.focus()
  }

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        enviar()
      }}
      className={cn(
        'w-full rounded-lg border-2 border-border bg-card p-3 shadow-md transition-colors focus-within:border-primary/60',
        className,
      )}
    >
      <AnimatePresence>
        {anexo && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden px-1"
          >
            <span className="mb-2 inline-flex items-center gap-1.5 rounded-full bg-secondary px-3 py-1 text-xs font-semibold text-secondary-foreground">
              <Paperclip className="size-3.5" aria-hidden />
              {anexo.name}
              <button
                type="button"
                onClick={() => setAnexo(null)}
                aria-label="Remover anexo"
                className="rounded-full hover:text-destructive"
              >
                <X className="size-3.5" />
              </button>
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      <textarea
        ref={textareaRef}
        rows={2}
        value={texto}
        autoFocus={autoFocus}
        onChange={(event) => setTexto(event.target.value)}
        onKeyDown={(event) => {
          // Enter envia; Shift+Enter quebra linha.
          if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
            event.preventDefault()
            enviar()
          }
        }}
        placeholder={ouvindo ? 'Ouvindo… pode falar' : 'Como posso ajudar você hoje?'}
        aria-label="Mensagem"
        className="w-full resize-none bg-transparent px-2 py-1 text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-0 focus-visible:ring-offset-0"
      />

      <div className="mt-1 flex items-center gap-2">
        <label
          htmlFor={arquivoId}
          title="Anexar arquivo"
          className="flex size-9 cursor-pointer items-center justify-center rounded-full text-primary transition-colors hover:bg-accent/60"
        >
          <Plus className="size-5" />
          <span className="sr-only">Anexar arquivo</span>
          <input
            id={arquivoId}
            type="file"
            className="sr-only"
            onChange={(event) => {
              setAnexo(event.target.files?.[0] ?? null)
              event.target.value = ''
            }}
          />
        </label>

        <div className="ml-auto flex items-center gap-1">
          <Select value={modo} onValueChange={(valor) => onModoChange(valor as ModoResposta)}>
            <SelectTrigger
              aria-label="Nível de detalhe da resposta"
              className="h-9 w-auto gap-2 border-none bg-transparent px-3 text-sm font-semibold text-muted-foreground hover:bg-muted"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent align="end">
              {modosResposta.map((opcao) => (
                <SelectItem key={opcao.valor} value={opcao.valor}>
                  {opcao.rotulo}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <button
            type="button"
            onClick={alternar}
            disabled={!suportado}
            aria-pressed={ouvindo}
            aria-label={ouvindo ? 'Parar ditado' : 'Ditar mensagem'}
            title={suportado ? 'Ditar por voz' : 'Ditado por voz não é suportado neste navegador'}
            className={cn(
              'relative flex size-9 items-center justify-center rounded-full transition-colors disabled:cursor-not-allowed disabled:opacity-40',
              ouvindo
                ? 'bg-destructive text-destructive-foreground'
                : 'text-primary hover:bg-accent/60',
            )}
          >
            {ouvindo && (
              <motion.span
                aria-hidden
                className="absolute inset-0 rounded-full bg-destructive"
                animate={{ scale: [1, 1.5], opacity: [0.5, 0] }}
                transition={{ duration: 1.2, repeat: Infinity }}
              />
            )}
            <Mic className="relative size-5" />
          </button>

          <Button
            type="submit"
            size="icon"
            disabled={!podeEnviar}
            aria-label="Enviar mensagem"
            className="size-9"
          >
            <ArrowUp />
          </Button>
        </div>
      </div>
    </form>
  )
}
