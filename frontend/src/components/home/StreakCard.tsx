import { motion } from 'framer-motion'
import { Check, Flame } from 'lucide-react'
import { useContagem } from '@/hooks/useContagem'
import { cn } from '@/lib/utils'

const letrasDaSemana = ['D', 'S', 'T', 'Q', 'Q', 'S', 'S']

/** Os últimos 7 dias terminando hoje, marcando os que entram na sequência atual. */
function ultimosSeteDias(streak: number) {
  const hoje = new Date()
  return Array.from({ length: 7 }, (_, i) => {
    const dia = new Date(hoje)
    dia.setDate(hoje.getDate() - (6 - i))
    return {
      chave: dia.toISOString().slice(0, 10),
      letra: letrasDaSemana[dia.getDay()],
      feito: i >= 7 - streak,
      hoje: i === 6,
    }
  })
}

export function StreakCard({ dias }: { dias: number }) {
  const contagem = useContagem(dias, { atraso: 0.3 })
  const semana = ultimosSeteDias(dias)

  return (
    <div className="relative overflow-hidden rounded-lg bg-gradient-to-br from-streak to-primary p-6 text-primary-foreground shadow-md">
      <div
        aria-hidden
        className="pointer-events-none absolute -bottom-16 -left-10 size-48 rounded-full bg-xp/40 blur-3xl"
      />

      <div className="relative flex items-center gap-5">
        <div className="relative flex size-20 shrink-0 items-center justify-center rounded-full bg-primary-foreground/20">
          <motion.span
            aria-hidden
            className="absolute inset-2 rounded-full bg-xp/50 blur-md"
            animate={{ opacity: [0.5, 1, 0.5], scale: [0.9, 1.1, 0.9] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          />
          <motion.span
            className="relative"
            animate={
              dias > 0 ? { scale: [1, 1.1, 0.96, 1.06, 1], rotate: [-3, 3, -2, 2, -3] } : undefined
            }
            transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
          >
            <Flame
              className={cn(
                'size-11',
                dias > 0 ? 'fill-xp text-primary-foreground' : 'text-primary-foreground/70',
              )}
            />
          </motion.span>
        </div>

        <div>
          <p className="font-display text-5xl font-extrabold leading-none">
            <span aria-hidden>{contagem}</span>
            <span className="sr-only">{dias}</span>
          </p>
          <p className="font-display text-lg font-bold">
            {dias === 1 ? 'dia seguido!' : 'dias seguidos!'}
          </p>
          {dias === 0 && (
            <p className="text-sm text-primary-foreground/90">
              Resolva um desafio hoje pra acender sua chama.
            </p>
          )}
        </div>
      </div>

      <ol className="relative mt-5 flex justify-between gap-1" aria-label="Últimos 7 dias">
        {semana.map((dia, i) => (
          <li key={dia.chave} className="flex flex-col items-center gap-1">
            <motion.span
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.4 + i * 0.06, type: 'spring', stiffness: 400, damping: 18 }}
              className={cn(
                'flex size-8 items-center justify-center rounded-full border-2 transition-colors',
                dia.feito
                  ? 'border-primary-foreground bg-primary-foreground text-streak'
                  : 'border-primary-foreground/40',
                dia.hoje && !dia.feito && 'border-dashed border-primary-foreground',
              )}
            >
              {dia.feito && <Check className="size-4" strokeWidth={3} />}
              <span className="sr-only">{dia.feito ? 'Estudou' : 'Não estudou'}</span>
            </motion.span>
            <span className={cn('text-xs font-bold', dia.hoje ? 'opacity-100' : 'opacity-70')}>
              {dia.letra}
            </span>
          </li>
        ))}
      </ol>
    </div>
  )
}
