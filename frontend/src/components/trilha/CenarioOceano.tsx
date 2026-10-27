import { motion } from 'framer-motion'
import { Fish } from 'lucide-react'
import { cn } from '@/lib/utils'

// Valores fixos (e não aleatórios) para o cenário não mudar a cada render.
const bolhas = [
  { left: 6, tamanho: 10, duracao: 9, atraso: 0 },
  { left: 14, tamanho: 6, duracao: 7, atraso: 2.5 },
  { left: 23, tamanho: 14, duracao: 11, atraso: 5 },
  { left: 38, tamanho: 8, duracao: 8, atraso: 1 },
  { left: 52, tamanho: 12, duracao: 10, atraso: 6 },
  { left: 63, tamanho: 6, duracao: 7, atraso: 3.5 },
  { left: 74, tamanho: 10, duracao: 9, atraso: 0.5 },
  { left: 86, tamanho: 16, duracao: 12, atraso: 4 },
  { left: 94, tamanho: 8, duracao: 8, atraso: 7 },
]

const algas = [
  { left: '1%', altura: 'h-40', cor: 'fill-success/35', atraso: 0 },
  { left: '4%', altura: 'h-28', cor: 'fill-periodo-1/50', atraso: 0.8 },
  { left: '7.5%', altura: 'h-20', cor: 'fill-success/25', atraso: 1.6 },
  { left: '89%', altura: 'h-24', cor: 'fill-periodo-1/45', atraso: 0.4 },
  { left: '93%', altura: 'h-36', cor: 'fill-success/30', atraso: 1.2 },
  { left: '96.5%', altura: 'h-16', cor: 'fill-periodo-1/40', atraso: 2 },
]

const raios = [
  { left: '12%', largura: 'w-16', duracao: 6 },
  { left: '34%', largura: 'w-24', duracao: 8 },
  { left: '61%', largura: 'w-12', duracao: 7 },
  { left: '80%', largura: 'w-20', duracao: 9 },
]

function Alga({ className, atraso, left }: { className: string; atraso: number; left: string }) {
  return (
    <motion.svg
      viewBox="0 0 40 160"
      className={cn('absolute bottom-6 w-8 origin-bottom', className)}
      style={{ left }}
      animate={{ rotate: [-5, 5, -5] }}
      transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut', delay: atraso }}
    >
      <path d="M20 160 C 4 130, 36 110, 18 80 C 2 55, 34 35, 20 0 C 30 30, 12 55, 28 80 C 44 110, 10 130, 26 160 Z" />
    </motion.svg>
  )
}

/**
 * Fundo do mar atrás do mapa da trilha: água em degradê, raios de luz,
 * bolhas, algas, areia com corais e peixinhos. Fica parado enquanto o mapa
 * rola por cima. Só cores dos tokens, para valer no escuro e no alto contraste.
 */
export function CenarioOceano() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-periodo-2/15 via-periodo-5/10 to-periodo-5/25" />

      {raios.map((raio) => (
        <motion.div
          key={raio.left}
          className={cn(
            'absolute -top-10 h-3/4 origin-top -skew-x-12 bg-gradient-to-b from-card/80 to-transparent',
            raio.largura,
          )}
          style={{ left: raio.left }}
          animate={{ opacity: [0.25, 0.6, 0.25] }}
          transition={{ duration: raio.duracao, repeat: Infinity, ease: 'easeInOut' }}
        />
      ))}

      {[
        { top: '22%', duracao: 22, atraso: 0, tamanho: 'size-6', cor: 'text-periodo-2/70' },
        { top: '58%', duracao: 28, atraso: 9, tamanho: 'size-8', cor: 'text-primary/50' },
        { top: '78%', duracao: 25, atraso: 16, tamanho: 'size-5', cor: 'text-periodo-6/70' },
      ].map((peixe) => (
        <motion.span
          key={peixe.top}
          className={cn('absolute', peixe.cor)}
          style={{ top: peixe.top }}
          initial={{ left: '-8%' }}
          animate={{ left: '108%', y: [0, -10, 0, 10, 0] }}
          transition={{
            left: {
              duration: peixe.duracao,
              repeat: Infinity,
              delay: peixe.atraso,
              ease: 'linear',
            },
            y: { duration: 4, repeat: Infinity, ease: 'easeInOut' },
          }}
        >
          <Fish className={cn(peixe.tamanho, 'fill-current')} />
        </motion.span>
      ))}

      {bolhas.map((bolha) => (
        <motion.span
          key={bolha.left}
          className="absolute rounded-full border-2 border-card/90 bg-card/30"
          style={{ left: `${bolha.left}%`, width: bolha.tamanho, height: bolha.tamanho }}
          initial={{ top: '105%', opacity: 0 }}
          animate={{ top: '-5%', opacity: [0, 0.9, 0.9, 0], x: [0, 8, -8, 0] }}
          transition={{
            duration: bolha.duracao,
            repeat: Infinity,
            delay: bolha.atraso,
            ease: 'easeIn',
          }}
        />
      ))}

      {algas.map((alga) => (
        <Alga
          key={alga.left}
          className={cn(alga.altura, alga.cor)}
          atraso={alga.atraso}
          left={alga.left}
        />
      ))}

      {/* Areia e corais no fundo. */}
      <svg
        viewBox="0 0 100 20"
        preserveAspectRatio="none"
        className="absolute bottom-0 left-0 h-16 w-full"
      >
        <path d="M0 9 Q 12 3 26 8 T 52 7 T 78 9 T 100 6 V20 H0 Z" className="fill-xp/25" />
        <path d="M0 14 Q 20 10 40 13 T 80 12 T 100 13 V20 H0 Z" className="fill-xp/30" />
      </svg>
      <span className="absolute bottom-3 left-[18%] h-6 w-10 rounded-t-full bg-primary/25" />
      <span className="absolute bottom-3 left-[21%] h-9 w-5 rounded-t-full bg-periodo-7/40" />
      <span className="absolute bottom-3 right-[20%] h-7 w-12 rounded-t-full bg-periodo-4/30" />
      <span className="absolute bottom-3 right-[17%] h-4 w-6 rounded-t-full bg-primary/30" />
    </div>
  )
}
