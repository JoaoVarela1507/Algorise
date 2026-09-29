import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

export function Secao({
  icone: Icone,
  titulo,
  descricao,
  children,
  className,
}: {
  icone: LucideIcon
  titulo: string
  descricao?: string
  children: ReactNode
  className?: string
}) {
  return (
    <section
      className={cn('rounded-lg border border-border bg-card p-6 shadow-sm', className)}
      aria-labelledby={`secao-${titulo}`}
    >
      <div className="mb-5 flex items-start gap-3">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary">
          <Icone className="size-5" aria-hidden />
        </span>
        <div>
          <h2 id={`secao-${titulo}`} className="font-display text-lg font-bold text-foreground">
            {titulo}
          </h2>
          {descricao && <p className="text-sm text-muted-foreground">{descricao}</p>}
        </div>
      </div>
      <div className="flex flex-col divide-y divide-border">{children}</div>
    </section>
  )
}

/** Uma linha de configuração: texto à esquerda, controle à direita. */
export function Opcao({
  titulo,
  descricao,
  children,
}: {
  titulo: string
  descricao?: string
  children: ReactNode
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3 py-4 first:pt-0 last:pb-0">
      <div className="min-w-0 flex-1 basis-56">
        <p className="font-semibold text-foreground">{titulo}</p>
        {descricao && <p className="text-sm text-muted-foreground">{descricao}</p>}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  )
}
