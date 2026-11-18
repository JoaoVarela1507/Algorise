import { useMemo, useRef, type KeyboardEvent } from 'react'
import hljs from 'highlight.js/lib/core'
import python from 'highlight.js/lib/languages/python'
import { cn } from '@/lib/utils'
import '@/components/chat/markdown-codigo.css'

hljs.registerLanguage('python', python)

const RECUO = '    '

/**
 * Editor de Python do desafio (#25), o mais leve possível: um `<textarea>`
 * transparente por cima do mesmo texto já colorido pelo highlight.js (só a
 * linguagem Python, alguns kB). Sem CodeMirror nem Monaco, que pesariam
 * centenas de kB para um editor de poucas linhas.
 *
 * Os dois têm a mesma fonte, o mesmo espaçamento e quebram linha igual, então o
 * cursor cai em cima da letra certa. Tab recua quatro espaços e o Enter mantém
 * o recuo da linha (e soma um depois de `:`), como num editor de verdade. O Esc
 * solta o foco, para o Tab voltar a navegar pela página.
 */
export function EditorDeCodigo({
  valor,
  aoMudar,
  rotulo,
  desabilitado = false,
  className,
}: {
  valor: string
  aoMudar: (valor: string) => void
  rotulo: string
  desabilitado?: boolean
  className?: string
}) {
  const campo = useRef<HTMLTextAreaElement>(null)
  // Escapado pelo highlight.js: o código do aluno nunca vira HTML.
  const colorido = useMemo(() => hljs.highlight(valor, { language: 'python' }).value, [valor])

  function inserir(texto: string, inicio: number, fim: number) {
    const novo = valor.slice(0, inicio) + texto + valor.slice(fim)
    aoMudar(novo)
    const cursor = inicio + texto.length
    requestAnimationFrame(() => campo.current?.setSelectionRange(cursor, cursor))
  }

  function teclar(evento: KeyboardEvent<HTMLTextAreaElement>) {
    const { selectionStart: inicio, selectionEnd: fim } = evento.currentTarget
    if (evento.key === 'Escape') {
      evento.currentTarget.blur()
    } else if (evento.key === 'Tab' && !evento.shiftKey) {
      evento.preventDefault()
      inserir(RECUO, inicio, fim)
    } else if (evento.key === 'Enter' && !evento.nativeEvent.isComposing) {
      evento.preventDefault()
      const linha = valor.slice(valor.lastIndexOf('\n', inicio - 1) + 1, inicio)
      const recuo = linha.match(/^\s*/)?.[0] ?? ''
      inserir(`\n${recuo}${linha.trimEnd().endsWith(':') ? RECUO : ''}`, inicio, fim)
    }
  }

  const texto = 'whitespace-pre-wrap break-words p-4 font-mono text-sm leading-6 [tab-size:4]'

  return (
    <div
      className={cn(
        'codigo-chat relative min-h-56 rounded-lg border border-border bg-muted focus-within:ring-2 focus-within:ring-ring',
        desabilitado && 'opacity-70',
        className,
      )}
    >
      {/* O espaço no fim mantém a altura da última linha vazia. */}
      <pre aria-hidden className={cn(texto, 'm-0 min-h-56 text-foreground')}>
        <code dangerouslySetInnerHTML={{ __html: `${colorido} ` }} />
      </pre>
      <textarea
        ref={campo}
        value={valor}
        onChange={(evento) => aoMudar(evento.target.value)}
        onKeyDown={teclar}
        disabled={desabilitado}
        aria-label={rotulo}
        aria-description="Tab recua a linha. Esc sai do editor."
        placeholder="# Escreva seu programa em Python aqui"
        spellCheck={false}
        autoCapitalize="off"
        autoComplete="off"
        autoCorrect="off"
        className={cn(
          texto,
          'absolute inset-0 size-full resize-none overflow-hidden bg-transparent text-transparent caret-foreground outline-none placeholder:text-muted-foreground selection:bg-primary/25',
        )}
      />
    </div>
  )
}
