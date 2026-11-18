import { useEffect, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { Flame, Star } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@/components/ui/dialog'
import { usePainel } from '@/hooks/useGamificacao'
import { cn } from '@/lib/utils'
import { useAccessibilityStore } from '@/stores/useAccessibilityStore'
import { useAuthStore } from '@/stores/useAuthStore'
import mascotePolvo from '@/assets/images/mascote-polvo.png'

/**
 * Os momentos que mereciam festa e passavam em branco (#31): subir de nível e
 * bater o recorde de dias seguidos. O fechamento de passo já tinha a dele
 * (`ModuloConcluido`); estes dois eram só um toast, ou nada.
 *
 * Observa o painel no cache (o check-in da Home, o XP ao vivo do WebSocket e as
 * submissões o atualizam) e compara com o último valor já comemorado, guardado
 * por aluno. Na primeira vez só guarda: não faz festa pelo que já existia.
 */

/** Recorde com menos dias que isso não é marco: 2 dias seguidos é o normal. */
const RECORDE_MINIMO = 3

type Marco = { tipo: 'nivel'; valor: number } | { tipo: 'recorde'; valor: number }

interface Visto {
  nivel: number
  recorde: number
}

function chaveDo(usuarioId: string) {
  return `algorise:comemorado:${usuarioId}`
}

function lerVisto(usuarioId: string): Visto | null {
  try {
    const salvo = localStorage.getItem(chaveDo(usuarioId))
    return salvo ? (JSON.parse(salvo) as Visto) : null
  } catch {
    return null
  }
}

function gravarVisto(usuarioId: string, visto: Visto) {
  try {
    localStorage.setItem(chaveDo(usuarioId), JSON.stringify(visto))
  } catch {
    // Sem storage: a festa pode se repetir na próxima visita, nada pior que isso.
  }
}

export function Comemoracoes() {
  const usuarioId = useAuthStore((estado) => estado.usuario?.id ?? null)
  // Só lê o cache: quem busca o painel são a Home e o Perfil.
  const painel = usePainel(false).data
  const [fila, setFila] = useState<Marco[]>([])

  useEffect(() => {
    if (!usuarioId || !painel) return
    const atual: Visto = { nivel: painel.nivel, recorde: painel.maior_streak }
    const visto = lerVisto(usuarioId)
    gravarVisto(usuarioId, {
      nivel: Math.max(atual.nivel, visto?.nivel ?? 0),
      recorde: Math.max(atual.recorde, visto?.recorde ?? 0),
    })
    if (!visto) return

    const novos: Marco[] = []
    if (atual.nivel > visto.nivel) novos.push({ tipo: 'nivel', valor: atual.nivel })
    if (atual.recorde > visto.recorde && atual.recorde >= RECORDE_MINIMO) {
      novos.push({ tipo: 'recorde', valor: atual.recorde })
    }
    if (novos.length) setFila((antes) => [...antes, ...novos])
  }, [usuarioId, painel])

  const marco = fila[0]
  return (
    <Dialog
      open={Boolean(marco)}
      onOpenChange={(aberto) => {
        if (!aberto) setFila((antes) => antes.slice(1))
      }}
    >
      {marco && (
        <DialogContent className="max-w-sm overflow-hidden text-center">
          <Festa key={`${marco.tipo}-${marco.valor}`} marco={marco} />
        </DialogContent>
      )}
    </Dialog>
  )
}

const CORES = ['bg-primary', 'bg-xp', 'bg-success', 'bg-periodo-2', 'bg-periodo-7', 'bg-streak']

// Posições fixas, como no `ModuloConcluido`: o mesmo desenho a cada render.
const CONFETES = Array.from({ length: 18 }, (_, i) => {
  const angulo = (i / 18) * Math.PI * 2
  const distancia = 110 + (i % 3) * 35
  return {
    x: Math.cos(angulo) * distancia,
    y: Math.sin(angulo) * distancia * 0.7 - 40,
    giro: (i % 2 ? 1 : -1) * (160 + i * 20),
    cor: CORES[i % CORES.length],
    redondo: i % 3 === 0,
  }
})

function Festa({ marco }: { marco: Marco }) {
  const doSistema = useReducedMotion()
  const doAluno = useAccessibilityStore((estado) => estado.reduzirAnimacoes)
  const parado = Boolean(doSistema) || doAluno
  const ehNivel = marco.tipo === 'nivel'

  return (
    <div className="relative flex flex-col items-center gap-3 pt-4">
      {!parado && (
        <div aria-hidden className="pointer-events-none absolute left-1/2 top-24">
          {CONFETES.map((confete, i) => (
            <motion.span
              key={i}
              className={cn(
                'absolute',
                confete.cor,
                confete.redondo ? 'size-2.5 rounded-full' : 'h-3 w-1.5 rounded-sm',
              )}
              initial={{ x: 0, y: 0, opacity: 1, rotate: 0 }}
              animate={{
                x: confete.x,
                y: [0, confete.y, confete.y + 200],
                opacity: [1, 1, 0],
                rotate: confete.giro,
              }}
              transition={{ duration: 1.8, delay: 0.1 + (i % 4) * 0.03, ease: 'easeOut' }}
            />
          ))}
        </div>
      )}

      <div className="relative">
        <motion.img
          src={mascotePolvo}
          alt=""
          className="relative z-10 h-28 select-none"
          draggable={false}
          initial={parado ? false : { scale: 0.5, y: 20, opacity: 0 }}
          animate={parado ? undefined : { scale: 1, y: [20, -12, 0], opacity: 1 }}
          // Mola só para a escala: o framer-motion não aceita mola com três
          // posições, e o pulo do `y` (sobe e assenta) vai por tempo.
          transition={{
            scale: { type: 'spring', stiffness: 260, damping: 14 },
            y: { duration: 0.6, ease: 'easeOut' },
            opacity: { duration: 0.2 },
          }}
        />
        <motion.span
          className={cn(
            'absolute -right-3 -top-2 z-20 flex size-12 items-center justify-center rounded-full shadow-lg',
            ehNivel ? 'bg-xp text-foreground' : 'bg-streak text-primary-foreground',
          )}
          initial={parado ? false : { scale: 0, rotate: -30 }}
          animate={parado ? undefined : { scale: 1, rotate: 0 }}
          transition={{ type: 'spring', stiffness: 400, damping: 12, delay: 0.25 }}
        >
          {ehNivel ? (
            <Star className="size-6 fill-current" aria-hidden />
          ) : (
            <Flame className="size-6 fill-current" aria-hidden />
          )}
        </motion.span>
      </div>

      <DialogTitle className="font-display text-3xl font-extrabold text-foreground">
        {ehNivel ? `Nível ${marco.valor}!` : `${marco.valor} dias seguidos!`}
      </DialogTitle>
      <DialogDescription className="text-muted-foreground">
        {ehNivel
          ? 'Você subiu de nível. Cada atividade conta: continue assim!'
          : 'É o seu novo recorde de sequência. Volte amanhã para aumentar.'}
      </DialogDescription>

      <DialogClose asChild>
        <Button size="lg" full className="mt-2">
          Bora continuar!
        </Button>
      </DialogClose>
    </div>
  )
}
