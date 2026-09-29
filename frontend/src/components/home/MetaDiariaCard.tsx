import { motion } from 'framer-motion'
import { Clock, Swords, Target } from 'lucide-react'
import { useContagem } from '@/hooks/useContagem'
import { cn } from '@/lib/utils'
import type { MetaDiaria } from '@/types/gamificacao'

const RAIO = 42
const CIRCUNFERENCIA = 2 * Math.PI * RAIO

export function MetaDiariaCard({ meta, className }: { meta: MetaDiaria; className?: string }) {
  const progresso = Math.min(meta.xpHoje / meta.xpMeta, 1)
  const xp = useContagem(meta.xpHoje, { atraso: 0.5 })
  const faltam = Math.max(meta.xpMeta - meta.xpHoje, 0)

  return (
    <div
      className={cn(
        'flex flex-col rounded-lg border border-border bg-card p-6 shadow-sm',
        className,
      )}
    >
      <div className="flex items-center gap-2">
        <Target className="size-5 text-primary" aria-hidden />
        <h2 className="font-display text-lg font-bold text-foreground">Meta diária</h2>
      </div>

      <div className="mt-4 flex flex-1 flex-col items-center justify-center gap-4 text-center">
        <div
          className="relative size-36 shrink-0"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={meta.xpMeta}
          aria-valuenow={meta.xpHoje}
          aria-label="XP de hoje"
        >
          <svg viewBox="0 0 100 100" className="size-full -rotate-90">
            <circle cx="50" cy="50" r={RAIO} strokeWidth="10" className="fill-none stroke-muted" />
            <motion.circle
              cx="50"
              cy="50"
              r={RAIO}
              strokeWidth="10"
              strokeLinecap="round"
              className="fill-none stroke-primary"
              strokeDasharray={CIRCUNFERENCIA}
              initial={{ strokeDashoffset: CIRCUNFERENCIA }}
              animate={{ strokeDashoffset: CIRCUNFERENCIA * (1 - progresso) }}
              transition={{ delay: 0.5, duration: 1, ease: 'easeOut' }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center" aria-hidden>
            <span className="font-display text-4xl font-extrabold leading-none text-foreground">
              {xp}
            </span>
            <span className="text-xs font-semibold text-muted-foreground">/ {meta.xpMeta} XP</span>
          </div>
        </div>

        <div className="flex flex-col items-center gap-3">
          <p className="text-sm text-muted-foreground">
            {faltam > 0 ? (
              <>
                Faltam <strong className="text-foreground">{faltam} XP</strong> para bater a meta de
                hoje.
              </>
            ) : (
              <strong className="text-success">Meta de hoje batida! 🎉</strong>
            )}
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            <span className="flex items-center gap-1.5 rounded-full bg-secondary px-3 py-1 text-xs font-bold text-secondary-foreground">
              <Swords className="size-3.5" aria-hidden />
              {meta.desafiosResolvidos} desafios
            </span>
            <span className="flex items-center gap-1.5 rounded-full bg-secondary px-3 py-1 text-xs font-bold text-secondary-foreground">
              <Clock className="size-3.5" aria-hidden />
              {meta.minutosEstudados} min
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
