import { motion } from 'framer-motion'
import { AvatarIniciais } from '@/components/home/AvatarIniciais'
import { saudacaoDoHorario } from '@/lib/tempo'
import mascotePolvo from '@/assets/images/mascote-polvo.png'

export function SaudacaoCard({ nome }: { nome: string }) {
  const agora = new Date()
  const primeiroNome = nome.split(' ')[0]
  const dataPorExtenso = new Intl.DateTimeFormat('pt-BR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  }).format(agora)

  return (
    <div className="relative flex items-center justify-between gap-6 overflow-hidden rounded-lg border border-border bg-card px-6 py-4 shadow-sm">
      <div
        aria-hidden
        className="pointer-events-none absolute -right-12 -top-20 size-64 rounded-full bg-accent/50 blur-3xl"
      />

      <div className="relative flex items-center gap-4">
        <AvatarIniciais nome={nome} className="size-16 text-xl ring-4 ring-primary/30" />
        <div>
          <p className="text-sm font-semibold text-muted-foreground first-letter:uppercase">
            {dataPorExtenso}
          </p>
          <h1 className="font-display text-2xl font-bold leading-tight text-foreground md:text-3xl">
            {saudacaoDoHorario(agora.getHours())},{' '}
            <span className="text-primary">{primeiroNome}</span>!
          </h1>
          <p className="text-muted-foreground">
            Bora manter o ritmo? Seu próximo desafio já está te esperando.
          </p>
        </div>
      </div>

      <motion.img
        src={mascotePolvo}
        alt=""
        className="relative hidden h-24 shrink-0 cursor-pointer select-none sm:block"
        animate={{ y: [0, -8, 0], rotate: [0, -3, 0] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
        whileHover={{ scale: 1.08, rotate: 8 }}
        whileTap={{ scale: 0.92 }}
        draggable={false}
      />
    </div>
  )
}
