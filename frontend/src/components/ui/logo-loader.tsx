import { motion, useReducedMotion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { useAccessibilityStore } from '@/stores/useAccessibilityStore'
import mascote from '@/assets/images/mascote-polvo.png'

/**
 * O carregando com a cara do Algorise: o polvo flutuando, com a sombra que
 * acompanha e bolhas subindo — o mesmo "polvo na água" do carrossel.
 *
 * Só decoração: quem anuncia o carregamento para o leitor de tela é o
 * `role="status"` de quem usa (`Carregando`). Com "Reduzir animações" (do
 * sistema ou das Configurações), o polvo fica parado.
 */

const TAMANHOS = {
  sm: { polvo: 'w-10', bolha: 4, altura: 'h-14' },
  md: { polvo: 'w-20', bolha: 6, altura: 'h-28' },
  lg: { polvo: 'w-28', bolha: 8, altura: 'h-40' },
} as const

const FLUTUAR = { duration: 1.6, repeat: Infinity, ease: 'easeInOut' } as const

// Posição horizontal e atraso de cada bolha: saem em sequência, não juntas.
const BOLHAS = [
  { x: '18%', atraso: 0 },
  { x: '78%', atraso: 0.55 },
  { x: '62%', atraso: 1.1 },
]

export function LogoLoader({
  tamanho = 'md',
  className,
}: {
  tamanho?: keyof typeof TAMANHOS
  className?: string
}) {
  const doSistema = useReducedMotion()
  const doAluno = useAccessibilityStore((estado) => estado.reduzirAnimacoes)
  const parado = Boolean(doSistema) || doAluno
  const medidas = TAMANHOS[tamanho]

  return (
    <div
      aria-hidden
      className={cn('relative flex flex-col items-center justify-end', medidas.altura, className)}
    >
      {!parado &&
        BOLHAS.map((bolha) => (
          <motion.span
            key={bolha.x}
            className="absolute bottom-1/3 rounded-full border border-primary/50 bg-primary/10"
            style={{ left: bolha.x, width: medidas.bolha, height: medidas.bolha }}
            initial={{ y: 0, opacity: 0, scale: 0.6 }}
            animate={{ y: '-260%', opacity: [0, 0.9, 0], scale: [0.6, 1, 1.15] }}
            // O y em porcentagem é do tamanho da bolha: sobe uns três diâmetros.
            transition={{ duration: 1.8, repeat: Infinity, delay: bolha.atraso, ease: 'easeOut' }}
          />
        ))}

      <motion.img
        src={mascote}
        alt=""
        draggable={false}
        className={cn('relative z-10 select-none', medidas.polvo)}
        animate={parado ? undefined : { y: [0, -8, 0], scaleY: [0.97, 1.02, 0.97] }}
        transition={FLUTUAR}
        style={{ originY: 1 }}
      />

      {/* A sombra encolhe quando o polvo sobe: é o que dá a sensação de altura. */}
      <motion.span
        className="mt-1 h-1.5 rounded-full bg-foreground/15"
        style={{ width: '60%' }}
        animate={parado ? undefined : { scaleX: [1, 0.7, 1], opacity: [0.6, 0.3, 0.6] }}
        transition={FLUTUAR}
      />
    </div>
  )
}

/** A tela inteira esperando: a sessão sendo restaurada ao recarregar. */
export function CarregandoTela({ rotulo = 'Carregando…' }: { rotulo?: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background text-muted-foreground"
    >
      <LogoLoader tamanho="lg" />
      <p className="text-sm font-semibold">{rotulo}</p>
    </div>
  )
}
