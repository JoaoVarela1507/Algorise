import { FileCode2, FileText, Image as IconeImagem, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { AnexoDoChat } from '@/services/chat'

const icones = { texto: FileCode2, pdf: FileText, imagem: IconeImagem } as const

function tamanhoLegivel(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/**
 * Chip de um anexo: no compositor leva o "remover"; na mensagem enviada, clicar
 * baixa o arquivo.
 */
export function ChipAnexo({
  anexo,
  aoRemover,
  aoBaixar,
  enviando = false,
  className,
}: {
  anexo: Pick<AnexoDoChat, 'nome' | 'tipo'> & { tamanho?: number }
  aoRemover?: () => void
  aoBaixar?: () => void
  /** O upload ainda está em andamento. */
  enviando?: boolean
  className?: string
}) {
  const Icone = icones[anexo.tipo as keyof typeof icones] ?? FileText
  const rotulo = (
    <>
      <Icone className="size-3.5 shrink-0" aria-hidden />
      <span className="truncate">{anexo.nome}</span>
      {anexo.tamanho !== undefined && (
        <span className="shrink-0 font-normal opacity-70">{tamanhoLegivel(anexo.tamanho)}</span>
      )}
      {enviando && <span className="shrink-0 font-normal opacity-70">enviando…</span>}
    </>
  )
  const estilo = cn(
    'inline-flex min-w-0 max-w-full items-center gap-1.5 rounded-full border border-border bg-secondary px-3 py-1 text-xs font-semibold text-secondary-foreground',
    className,
  )

  return (
    <span className={estilo}>
      {aoBaixar ? (
        <button
          type="button"
          onClick={aoBaixar}
          title="Baixar anexo"
          className="inline-flex min-w-0 items-center gap-1.5 hover:underline"
        >
          {rotulo}
        </button>
      ) : (
        rotulo
      )}
      {aoRemover && (
        <button
          type="button"
          onClick={aoRemover}
          aria-label={`Remover anexo ${anexo.nome}`}
          className="shrink-0 rounded-full hover:text-destructive"
        >
          <X className="size-3.5" />
        </button>
      )}
    </span>
  )
}
