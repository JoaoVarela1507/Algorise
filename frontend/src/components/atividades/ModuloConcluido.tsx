import { useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { ArrowRight, Sparkles, Star, Trophy } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useContagem } from '@/hooks/useContagem'
import { cn } from '@/lib/utils'
import mascotePolvo from '@/assets/images/mascote-polvo.png'

const CORES = ['bg-primary', 'bg-xp', 'bg-success', 'bg-periodo-2', 'bg-periodo-7', 'bg-streak']

/**
 * Confete saindo do centro, em leque. Posições fixas (e não `Math.random`)
 * para o desenho ser o mesmo a cada render e nos testes.
 */
const CONFETES = Array.from({ length: 28 }, (_, i) => {
  const angulo = (i / 28) * Math.PI * 2
  const distancia = 160 + (i % 4) * 45
  return {
    x: Math.cos(angulo) * distancia,
    // Sobe mais do que desce, e depois a "gravidade" puxa tudo para baixo.
    y: Math.sin(angulo) * distancia * 0.7 - 60,
    giro: (i % 2 ? 1 : -1) * (180 + i * 25),
    cor: CORES[i % CORES.length],
    redondo: i % 3 === 0,
    atraso: (i % 5) * 0.03,
  }
})

/**
 * A comemoração de fechar um passo (tela 38): confete, o polvo pulando, o XP
 * ganho subindo e o caminho de volta para o mapa, onde o polvo já está no
 * módulo seguinte.
 */
export function ModuloConcluido({
  titulo,
  xpGanho,
  proximo,
  aoContinuar,
}: {
  /** O módulo que acabou de fechar. */
  titulo: string
  xpGanho: number
  /** Ordem do módulo seguinte; `null` quando era o último da trilha. */
  proximo: number | null
  aoContinuar: () => void
}) {
  const botao = useRef<HTMLButtonElement>(null)
  const xp = useContagem(xpGanho, { atraso: 0.6 })
  const fimDaTrilha = proximo === null

  // O foco vai para a única ação da tela, como num diálogo.
  useEffect(() => botao.current?.focus(), [])

  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 p-4 backdrop-blur-sm"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modulo-concluido-titulo"
      onKeyDown={(evento) => evento.key === 'Escape' && aoContinuar()}
    >
      <motion.div
        className={cn(
          'relative w-full max-w-md overflow-hidden rounded-2xl border p-8 text-center shadow-2xl',
          fimDaTrilha ? 'border-xp/60 bg-card' : 'border-border bg-card',
        )}
        initial={{ scale: 0.6, y: 40, opacity: 0 }}
        animate={{ scale: 1, y: 0, opacity: 1 }}
        transition={{ type: 'spring', stiffness: 260, damping: 18 }}
      >
        {/* Brilho no fundo, girando devagar atrás do polvo. */}
        <motion.div
          aria-hidden
          className="pointer-events-none absolute left-1/2 top-24 size-72 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[conic-gradient(from_0deg,transparent,hsl(var(--xp)/0.35),transparent,hsl(var(--primary)/0.3),transparent)] blur-xl"
          animate={{ rotate: 360 }}
          transition={{ duration: 12, repeat: Infinity, ease: 'linear' }}
        />

        <div aria-hidden className="pointer-events-none absolute left-1/2 top-24">
          {CONFETES.map((confete, i) => (
            <motion.span
              key={i}
              className={cn(
                'absolute block',
                confete.cor,
                confete.redondo ? 'size-2.5 rounded-full' : 'h-3 w-1.5 rounded-sm',
              )}
              initial={{ x: 0, y: 0, opacity: 0, rotate: 0, scale: 0.4 }}
              animate={{
                x: confete.x,
                y: [0, confete.y, confete.y + 260],
                opacity: [0, 1, 1, 0],
                rotate: confete.giro,
                scale: 1,
              }}
              transition={{ duration: 2.2, delay: 0.15 + confete.atraso, ease: 'easeOut' }}
            />
          ))}
        </div>

        <motion.img
          src={mascotePolvo}
          alt=""
          draggable={false}
          className="relative mx-auto h-32 select-none drop-shadow-lg"
          initial={{ y: 30, scale: 0.5 }}
          animate={{ y: [30, -18, 0, -8, 0], scale: 1, rotate: [0, -8, 8, -4, 0] }}
          transition={{ duration: 1.1, delay: 0.1, ease: 'easeOut' }}
        />

        <motion.div
          className="relative mt-4 flex flex-col items-center gap-2"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
        >
          <span className="flex items-center gap-1.5 rounded-full bg-success/15 px-3 py-1 text-xs font-bold uppercase tracking-wide text-success">
            {fimDaTrilha ? (
              <Trophy className="size-3.5" aria-hidden />
            ) : (
              <Sparkles className="size-3.5" aria-hidden />
            )}
            {fimDaTrilha ? 'Trilha concluída' : 'Módulo concluído'}
          </span>
          <h2
            id="modulo-concluido-titulo"
            className="font-display text-3xl font-extrabold leading-tight text-foreground"
          >
            {fimDaTrilha ? 'Você zerou a trilha!' : 'Mandou bem!'}
          </h2>
          <p className="text-muted-foreground">
            Você fechou <strong className="text-foreground">{titulo}</strong>.
            {fimDaTrilha
              ? ' Todos os módulos estão concluídos.'
              : ` O módulo ${proximo} já está liberado no caminho.`}
          </p>
        </motion.div>

        {xpGanho > 0 && (
          <motion.p
            className="relative mx-auto mt-5 flex w-fit items-center gap-2 rounded-full bg-xp/20 px-5 py-2 font-display text-2xl font-extrabold text-streak"
            initial={{ scale: 0 }}
            animate={{ scale: [0, 1.2, 1] }}
            transition={{ delay: 0.55, duration: 0.5 }}
          >
            <motion.span
              animate={{ rotate: [0, 20, -20, 0] }}
              transition={{ delay: 1, duration: 0.6 }}
            >
              <Star className="size-6 fill-xp text-xp" aria-hidden />
            </motion.span>
            <span aria-hidden>+{xp} XP</span>
            <span className="sr-only">Você ganhou {xpGanho} XP</span>
          </motion.p>
        )}

        <motion.div
          className="relative mt-7"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.75 }}
        >
          <Button ref={botao} size="lg" full className="group" onClick={aoContinuar}>
            {fimDaTrilha ? 'Ver a trilha completa' : 'Voltar para o caminho'}
            <ArrowRight className="transition-transform group-hover:translate-x-1" />
          </Button>
        </motion.div>
      </motion.div>
    </motion.div>
  )
}
