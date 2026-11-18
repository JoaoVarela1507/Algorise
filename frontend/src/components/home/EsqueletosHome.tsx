import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

/**
 * Esqueletos dos cards da Home: o formato de cada um enquanto os dados chegam.
 *
 * Antes eram quatro "Carregando…" de altura qualquer ao mesmo tempo, e a tela
 * pulava quando cada card trocava o spinner pelo conteúdo. Com o esqueleto no
 * tamanho do card, o conteúdo entra no lugar dele sem empurrar nada.
 */

function Moldura({
  rotulo,
  className,
  children,
}: {
  rotulo: string
  className?: string
  children: ReactNode
}) {
  return (
    <div
      role="status"
      aria-busy="true"
      className={cn(
        'flex flex-col rounded-lg border border-border bg-card p-4 shadow-sm sm:p-6',
        className,
      )}
    >
      <span className="sr-only">{rotulo}</span>
      <div aria-hidden className="contents">
        {children}
      </div>
    </div>
  )
}

function Linha({ className }: { className?: string }) {
  return <div className={cn('esqueleto h-4', className)} />
}

export function EsqueletoRanking({ className }: { className?: string }) {
  return (
    <Moldura rotulo="Carregando ranking…" className={className}>
      <Linha className="mx-auto h-6 w-3/4" />
      <div className="mt-6 grid flex-1 grid-cols-[minmax(0,1fr)] items-end gap-6 sm:grid-cols-[auto_1fr] xl:grid-cols-1 2xl:grid-cols-[auto_1fr]">
        <div className="esqueleto mx-auto h-48 w-full max-w-[11rem] rounded-lg" />
        <div className="flex items-end justify-center gap-2 sm:gap-3">
          {['h-28', 'h-40', 'h-20'].map((altura) => (
            <div key={altura} className="flex w-24 flex-col items-center gap-2 sm:w-28">
              <div className="esqueleto size-14 rounded-full" />
              <div className={cn('esqueleto w-full rounded-b-none rounded-t-lg', altura)} />
            </div>
          ))}
        </div>
      </div>
      <Linha className="mx-auto mt-4 w-32" />
    </Moldura>
  )
}

export function EsqueletoTrilhaAtual() {
  return (
    <Moldura rotulo="Carregando trilha…">
      <Linha className="w-24 rounded-full" />
      <div className="mt-4 flex items-center gap-3">
        <div className="esqueleto size-12 shrink-0 rounded-lg" />
        <div className="flex flex-1 flex-col gap-2">
          <Linha className="h-5 w-2/3" />
          <Linha className="w-1/2" />
        </div>
      </div>
      <Linha className="mt-5 h-3 w-full rounded-full" />
      <div className="esqueleto mt-5 h-12 w-full rounded-full" />
    </Moldura>
  )
}

export function EsqueletoConquistas({ className }: { className?: string }) {
  return (
    <Moldura rotulo="Carregando conquistas…" className={className}>
      <div className="flex items-center justify-between">
        <Linha className="h-5 w-28" />
        <Linha className="w-12 rounded-full" />
      </div>
      <div className="mt-5 grid grid-cols-3 gap-4">
        {Array.from({ length: 6 }, (_, i) => (
          <div key={i} className="flex flex-col items-center gap-2">
            <div className="esqueleto size-14 rounded-full" />
            <Linha className="h-3 w-16" />
          </div>
        ))}
      </div>
    </Moldura>
  )
}

export function EsqueletoMetaDiaria({ className }: { className?: string }) {
  return (
    <Moldura rotulo="Carregando meta do dia…" className={className}>
      <Linha className="h-5 w-32" />
      <div className="esqueleto mx-auto mt-5 size-40 rounded-full" />
      <Linha className="mx-auto mt-5 w-3/4" />
    </Moldura>
  )
}
