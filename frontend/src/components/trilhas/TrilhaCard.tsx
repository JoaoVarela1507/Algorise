import { Link } from 'react-router-dom'
import { motion, useAnimate } from 'framer-motion'
import { Check, Lock, Play, Sparkles } from 'lucide-react'
import { coresPeriodo } from '@/components/trilhas/periodos'
import { cn } from '@/lib/utils'
import type { CategoriaTrilha, TrilhaResumo } from '@/types/trilha'

const coresCategoria: Record<CategoriaTrilha, string> = {
  Linguagens: 'bg-periodo-5/40',
  Gerais: 'bg-periodo-2/40',
  Fundamentos: 'bg-periodo-3/40',
  Infraestrutura: 'bg-periodo-1/40',
  Dados: 'bg-periodo-6/40',
}

const selo = 'rounded-full px-3 py-0.5 text-xs font-bold'

export function TrilhaCard({ trilha }: { trilha: TrilhaResumo }) {
  const [escopoIcone, animar] = useAnimate()
  const concluida = trilha.modulosConcluidos >= trilha.totalModulos
  const porcentagem = Math.round((trilha.modulosConcluidos / trilha.totalModulos) * 100)

  const conteudo = (
    <>
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-wrap gap-2">
          <span className={cn(selo, 'text-periodo-foreground', coresCategoria[trilha.categoria])}>
            {trilha.categoria}
          </span>
          <span
            className={cn(
              selo,
              'border border-border bg-card',
              concluida ? 'text-success' : 'text-streak',
            )}
          >
            {trilha.modulosConcluidos}/{trilha.totalModulos}
          </span>
          <span
            className={cn(selo, 'text-periodo-foreground', coresPeriodo[trilha.periodo]?.cheio)}
          >
            {trilha.periodo}º Período
          </span>
        </div>

        <span
          ref={escopoIcone}
          className={cn(
            'flex size-14 shrink-0 items-center justify-center rounded-full shadow-sm transition-all duration-300',
            trilha.bloqueada && 'bg-card text-locked',
            !trilha.bloqueada &&
              concluida &&
              'bg-success text-success-foreground group-hover:scale-110',
            !trilha.bloqueada &&
              !concluida &&
              'bg-card text-primary group-hover:scale-110 group-hover:bg-primary group-hover:text-primary-foreground',
          )}
          aria-hidden
        >
          {trilha.bloqueada ? (
            <Lock className="size-6" />
          ) : concluida ? (
            <Check className="size-7" strokeWidth={3} />
          ) : (
            <Play className="ml-1 size-6 fill-current" />
          )}
        </span>
      </div>

      <h2 className="font-display text-xl font-bold leading-tight text-foreground">
        {trilha.nome}
      </h2>

      {trilha.bloqueada ? (
        <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <Lock className="size-3.5 shrink-0" aria-hidden />
          Conclua <strong className="font-semibold">{trilha.requisito}</strong> para desbloquear
        </p>
      ) : (
        <div className="flex items-center gap-3">
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
            <motion.div
              className="h-full rounded-full bg-success"
              initial={{ width: 0 }}
              animate={{ width: `${porcentagem}%` }}
              transition={{ delay: 0.3, duration: 0.7, ease: 'easeOut' }}
            />
          </div>
          <span className="text-xs font-bold text-muted-foreground">{porcentagem}%</span>
        </div>
      )}

      <p className="mt-auto flex items-center gap-1.5 text-sm font-semibold text-muted-foreground">
        {trilha.recomendada && <Sparkles className="size-4 text-xp" aria-hidden />}
        {trilha.motivo}
      </p>
    </>
  )

  const base =
    'group flex h-full w-full flex-col gap-3 rounded-lg border bg-card p-5 text-left shadow-sm transition-all duration-300'

  if (trilha.bloqueada) {
    return (
      <button
        type="button"
        aria-disabled="true"
        aria-label={`${trilha.nome}, bloqueada. Conclua ${trilha.requisito} para desbloquear.`}
        onClick={() => animar(escopoIcone.current, { x: [0, -6, 6, -4, 4, 0] }, { duration: 0.4 })}
        className={cn(base, 'cursor-not-allowed border-border bg-card/60')}
      >
        {conteudo}
      </button>
    )
  }

  return (
    <Link
      to={`/trilhas/${trilha.id}/questao/1`}
      className={cn(
        base,
        'hover:-translate-y-1 hover:border-primary/50 hover:shadow-md',
        trilha.recomendada ? 'border-primary/40 ring-2 ring-primary/20' : 'border-border',
      )}
    >
      {conteudo}
    </Link>
  )
}
