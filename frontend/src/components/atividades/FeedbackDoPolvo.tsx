import { motion, useReducedMotion } from 'framer-motion'
import { Lightbulb, Sparkles } from 'lucide-react'
import type { Correcao } from '@/hooks/useAtividades'
import { LogoLoader } from '@/components/ui/logo-loader'
import { cn } from '@/lib/utils'
import { useAccessibilityStore } from '@/stores/useAccessibilityStore'
import mascotePolvo from '@/assets/images/mascote-polvo.png'

/**
 * O retorno da resposta aberta com o mascote (#22): o polvo comemora o acerto
 * ("EXATAMENTE!!!") ou mostra o que faltou ("Quase lá!"), com a pista que a IA
 * deu, sem entregar o gabarito.
 *
 * Enquanto a IA corrige, o polvo fica "lendo": a correção leva uns segundos, e
 * um botão parado nesse tempo parece travado. Em análise (a IA não respondeu)
 * quem fala é a moldura, como antes.
 */
export function FeedbackDoPolvo({ correcao }: { correcao: Correcao }) {
  const doSistema = useReducedMotion()
  const doAluno = useAccessibilityStore((estado) => estado.reduzirAnimacoes)
  const parado = Boolean(doSistema) || doAluno
  const { estado, feedback, sugestao, enviando, rodada } = correcao

  if (enviando) {
    return (
      <div
        role="status"
        className="flex items-center gap-3 rounded-xl border border-border bg-card p-3"
      >
        <LogoLoader tamanho="sm" />
        <p className="text-sm font-semibold text-muted-foreground">
          O polvo está lendo sua resposta…
        </p>
      </div>
    )
  }

  if (estado !== 'certa' && estado !== 'errada') return null
  // O acerto já salvo (aluno voltou à atividade) não tem fala nova para mostrar.
  if (rodada === 0) return null
  const acertou = estado === 'certa'

  return (
    <motion.div
      key={rodada}
      role="status"
      className={cn(
        'grid grid-cols-[auto_minmax(0,1fr)] items-start gap-3 rounded-xl border-2 p-3 sm:gap-4 sm:p-4',
        acertou ? 'border-success/40 bg-success/10' : 'border-xp/50 bg-xp/10',
      )}
      initial={parado ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
    >
      <motion.img
        src={mascotePolvo}
        alt=""
        draggable={false}
        className="w-16 select-none sm:w-20"
        initial={parado ? false : acertou ? { y: 10, scale: 0.8 } : { rotate: 0 }}
        animate={
          parado
            ? undefined
            : acertou
              ? { y: [10, -10, 0], scale: 1 }
              : { rotate: [0, -8, 6, -4, 0] }
        }
        transition={
          acertou
            ? { y: { duration: 0.55, ease: 'easeOut' }, scale: { duration: 0.3 } }
            : { duration: 0.6, ease: 'easeInOut' }
        }
      />

      <div className="flex min-w-0 flex-col gap-1.5">
        <p
          className={cn(
            'flex items-center gap-1.5 font-display text-xl font-extrabold tracking-tight',
            acertou ? 'text-success' : 'text-foreground',
          )}
        >
          {acertou ? (
            <>
              EXATAMENTE!!!
              <Sparkles className="size-5 text-xp" aria-hidden />
            </>
          ) : (
            'Quase lá!'
          )}
        </p>
        {feedback && <p className="text-sm text-foreground">{feedback}</p>}
        {!acertou && sugestao && (
          <p className="mt-1 flex gap-2 rounded-lg bg-card p-2.5 text-sm text-foreground">
            <Lightbulb className="mt-0.5 size-4 shrink-0 text-xp" aria-hidden />
            <span>
              <span className="font-bold">O que faltou: </span>
              {sugestao}
            </span>
          </p>
        )}
        {!acertou && (
          <p className="text-xs text-muted-foreground">Ajuste sua resposta e envie de novo.</p>
        )}
      </div>
    </motion.div>
  )
}
