import { motion } from 'framer-motion'
import { Lock, Trophy } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Conquista } from '@/types/gamificacao'

export function ConquistasCard({
  conquistas,
  className,
}: {
  conquistas: Conquista[]
  className?: string
}) {
  const desbloqueadas = conquistas.filter((c) => c.desbloqueada).length

  return (
    <div
      className={cn(
        'flex flex-col rounded-lg border border-border bg-card p-6 shadow-sm',
        className,
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Trophy className="size-5 text-xp" aria-hidden />
          <h2 className="font-display text-lg font-bold text-foreground">Conquistas</h2>
        </div>
        <span className="rounded-full bg-secondary px-3 py-1 text-xs font-bold text-muted-foreground">
          {desbloqueadas} de {conquistas.length}
        </span>
      </div>

      {/* Na coluna estreita do desktop cabem 3 por linha; em tablet, 6 numa linha só. */}
      <ul className="mt-4 grid flex-1 grid-cols-3 content-center gap-x-3 gap-y-5 sm:grid-cols-6 xl:grid-cols-3">
        {conquistas.map((conquista, i) => (
          <motion.li
            key={conquista.id}
            initial={{ opacity: 0, scale: 0.6 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.4 + i * 0.07, type: 'spring', stiffness: 300, damping: 16 }}
            className="group flex flex-col items-center gap-2 text-center"
            title={conquista.descricao}
          >
            <motion.span
              whileHover={
                conquista.desbloqueada ? { rotate: [0, -12, 12, -6, 0], scale: 1.1 } : undefined
              }
              transition={{ duration: 0.5 }}
              className={cn(
                'relative flex size-14 items-center justify-center rounded-full border-2',
                conquista.desbloqueada
                  ? 'border-xp bg-xp/20 text-streak shadow-sm'
                  : 'border-dashed border-locked/60 bg-muted text-locked',
              )}
            >
              <conquista.icone className="size-6" aria-hidden />
              {!conquista.desbloqueada && (
                <span className="absolute -bottom-1 -right-1 flex size-5 items-center justify-center rounded-full bg-card">
                  <Lock className="size-3" aria-hidden />
                </span>
              )}
            </motion.span>
            <span
              className={cn(
                'text-xs font-bold leading-tight',
                conquista.desbloqueada ? 'text-foreground' : 'text-muted-foreground',
              )}
            >
              {conquista.titulo}
              <span className="sr-only">
                {conquista.desbloqueada ? ' (desbloqueada)' : ' (bloqueada)'}: {conquista.descricao}
              </span>
            </span>
          </motion.li>
        ))}
      </ul>
    </div>
  )
}
