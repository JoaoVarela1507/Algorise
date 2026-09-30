import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, Lock, Network } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { TrilhaAtual } from '@/types/ranking'

export function TrilhaAtualCard({
  trilha,
  className,
}: {
  trilha: TrilhaAtual
  className?: string
}) {
  const { modulosConcluidos, totalModulos } = trilha
  const moduloAtual = Math.min(modulosConcluidos + 1, totalModulos)
  const naoComecou = modulosConcluidos === 0

  return (
    <div
      className={cn(
        'flex flex-col rounded-lg border border-border bg-card p-6 shadow-sm',
        className,
      )}
    >
      <span className="self-start rounded-full bg-secondary px-3 py-1 text-xs font-bold uppercase tracking-wide text-muted-foreground">
        Trilha atual
      </span>

      <div className="mt-4 flex items-center gap-4">
        <motion.div
          whileHover={{ rotate: -8, scale: 1.05 }}
          className="flex size-14 shrink-0 items-center justify-center rounded-lg bg-success text-success-foreground shadow-sm"
        >
          <Network className="size-7" />
        </motion.div>
        <div className="min-w-0">
          <h2 className="font-display text-xl font-bold leading-tight text-foreground">
            {trilha.nome}
          </h2>
          <p className="truncate text-sm text-muted-foreground">
            {trilha.disciplina} · Próximo: {trilha.proximoModulo}
          </p>
        </div>
      </div>

      <div className="mt-5">
        <div className="mb-2 flex items-center justify-between text-sm font-semibold">
          <span className="text-foreground">
            Módulo {moduloAtual} de {totalModulos}
          </span>
          <span className="text-muted-foreground">
            {Math.round((modulosConcluidos / totalModulos) * 100)}%
          </span>
        </div>

        <div
          className="flex items-center gap-1"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={totalModulos}
          aria-valuenow={modulosConcluidos}
          aria-label="Módulos concluídos"
        >
          {Array.from({ length: totalModulos }, (_, i) => {
            const concluido = i < modulosConcluidos
            const atual = i === modulosConcluidos
            return (
              <motion.span
                key={i}
                initial={{ scaleX: 0 }}
                animate={{ scaleX: 1 }}
                style={{ originX: 0 }}
                transition={{ delay: 0.5 + i * 0.05, duration: 0.3 }}
                className={cn(
                  'h-3 flex-1 rounded-full',
                  concluido && 'bg-success',
                  atual && 'animate-pulse bg-primary',
                  !concluido && !atual && 'bg-muted',
                )}
              />
            )
          })}
          <Lock className="ml-1 size-4 shrink-0 text-locked" aria-hidden />
        </div>
      </div>

      <div className="mt-auto pt-6">
        <Button asChild full size="lg" className="group">
          <Link to="/trilhas">
            {naoComecou ? 'Começar trilha' : 'Continuar trilha'}
            <ArrowRight className="transition-transform group-hover:translate-x-1" />
          </Link>
        </Button>
      </div>
    </div>
  )
}
