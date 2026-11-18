import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Check, Copy } from 'lucide-react'
import { rotuloDaLinguagem, textoDe } from './codigoUtil'
import './markdown-codigo.css'

/**
 * Bloco de código com rótulo da linguagem e botão "Copiar".
 * O botão fica sempre visível (sem hover) porque no celular não há hover; e o
 * <pre> rola na horizontal sozinho, para linha longa não alargar a página.
 */
export function CodigoBloco({ linguagem, children }: { linguagem?: string; children: ReactNode }) {
  const [copiado, setCopiado] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined)

  useEffect(() => () => clearTimeout(timerRef.current), [])

  async function copiar() {
    try {
      await navigator.clipboard.writeText(textoDe(children).replace(/\n$/, ''))
      setCopiado(true)
      clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => setCopiado(false), 2000)
    } catch {
      // Sem permissão de área de transferência (http, navegador antigo): o
      // texto continua selecionável no bloco, então não há o que avisar.
    }
  }

  return (
    <div className="codigo-chat my-1 max-w-full overflow-hidden rounded-lg border border-border bg-muted text-foreground">
      <div className="flex items-center justify-between gap-2 border-b border-border px-3 py-1">
        <span className="text-xs font-semibold text-muted-foreground">
          {rotuloDaLinguagem(linguagem)}
        </span>
        <button
          type="button"
          onClick={copiar}
          aria-label={copiado ? 'Código copiado' : 'Copiar código'}
          className="flex min-h-8 items-center gap-1.5 rounded px-2 text-xs font-semibold text-muted-foreground transition-colors hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
        >
          {copiado ? (
            <Check className="size-3.5" aria-hidden />
          ) : (
            <Copy className="size-3.5" aria-hidden />
          )}
          <span aria-live="polite">{copiado ? 'Copiado!' : 'Copiar'}</span>
        </button>
      </div>
      <pre className="overflow-x-auto p-3 font-mono text-sm leading-relaxed">
        <code>{children}</code>
      </pre>
    </div>
  )
}
