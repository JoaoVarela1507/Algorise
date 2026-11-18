import { useId, useLayoutEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowUp, Mic, Plus } from 'lucide-react'
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
import { mensagemDeErro } from '@/components/chat/erros'
import {
  ACCEPT_ANEXOS,
  ANEXOS_POR_MENSAGEM,
  apagarAnexo,
  enviarAnexo,
  modosResposta,
  validarAnexo,
  type AnexoDoChat,
} from '@/services/chat'
import type { ModoResposta } from '@/types/chat'
import { ChipAnexo } from './ChipAnexo'

const ALTURA_MAXIMA = 200

/** Um anexo no compositor: sobe assim que é escolhido, e o id vai com a mensagem. */
interface AnexoNoCompositor {
  chave: string
  nome: string
  /** Só existe depois do upload. */
  enviado?: AnexoDoChat
}

function tipoPelaExtensao(nome: string): string {
  if (/\.pdf$/i.test(nome)) return 'pdf'
  if (/\.(png|jpe?g|webp)$/i.test(nome)) return 'imagem'
  return 'texto'
}

export function Composer({
  onEnviar,
  ocupado,
  modo,
  onModoChange,
  autoFocus,
  className,
}: {
  onEnviar: (texto: string, anexos: AnexoDoChat[]) => void
  ocupado: boolean
  modo: ModoResposta
  onModoChange: (modo: ModoResposta) => void
  autoFocus?: boolean
  className?: string
}) {
  const [texto, setTexto] = useState('')
  const [anexos, setAnexos] = useState<AnexoNoCompositor[]>([])
  const [erroAnexo, setErroAnexo] = useState<string | null>(null)
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

  const subindo = anexos.some((item) => !item.enviado)
  const podeEnviar = texto.trim().length > 0 && !ocupado && !subindo

  function enviar() {
    if (!podeEnviar) return
    onEnviar(
      texto.trim(),
      anexos.flatMap((item) => (item.enviado ? [item.enviado] : [])),
    )
    setTexto('')
    setAnexos([])
    setErroAnexo(null)
    textareaRef.current?.focus()
  }

  async function anexar(arquivos: FileList | null) {
    setErroAnexo(null)
    const escolhidos = Array.from(arquivos ?? [])
    const vagas = ANEXOS_POR_MENSAGEM - anexos.length
    if (escolhidos.length > vagas) {
      setErroAnexo(`Cada mensagem aceita até ${ANEXOS_POR_MENSAGEM} anexos.`)
    }
    for (const arquivo of escolhidos.slice(0, Math.max(vagas, 0))) {
      const invalido = validarAnexo(arquivo)
      if (invalido) {
        setErroAnexo(invalido)
        continue
      }
      const chave = crypto.randomUUID()
      setAnexos((atuais) => [...atuais, { chave, nome: arquivo.name }])
      try {
        const enviado = await enviarAnexo(arquivo)
        setAnexos((atuais) =>
          atuais.map((item) => (item.chave === chave ? { ...item, enviado } : item)),
        )
      } catch (erro) {
        setAnexos((atuais) => atuais.filter((item) => item.chave !== chave))
        setErroAnexo(mensagemDeErro(erro))
      }
    }
  }

  function removerAnexo(item: AnexoNoCompositor) {
    setAnexos((atuais) => atuais.filter((outro) => outro.chave !== item.chave))
    // Desistir apaga o arquivo no servidor; se falhar, ele fica solto e some sozinho.
    if (item.enviado) void apagarAnexo(item.enviado.id).catch(() => undefined)
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
        {anexos.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden px-1"
          >
            <div className="mb-2 flex flex-wrap gap-2">
              {anexos.map((item) => (
                <ChipAnexo
                  key={item.chave}
                  anexo={item.enviado ?? { nome: item.nome, tipo: tipoPelaExtensao(item.nome) }}
                  enviando={!item.enviado}
                  aoRemover={() => removerAnexo(item)}
                />
              ))}
            </div>
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
            multiple
            accept={ACCEPT_ANEXOS}
            className="sr-only"
            onChange={(event) => {
              void anexar(event.target.files)
              event.target.value = ''
            }}
          />
        </label>
        {erroAnexo && (
          <p role="alert" className="min-w-0 flex-1 text-xs font-semibold text-destructive">
            {erroAnexo}
          </p>
        )}

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
