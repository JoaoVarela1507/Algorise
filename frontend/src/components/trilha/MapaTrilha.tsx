import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { motion, useAnimate } from 'framer-motion'
import { Check, Lock, Play } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ModuloTrilha } from '@/types/trilha'
import mascotePolvo from '@/assets/images/mascote-polvo.png'

interface Ponto {
  x: number
  y: number
}

// Tudo em pixels reais: o SVG não é esticado, então o traço verde animado
// (pathLength) fica contínuo. Com `preserveAspectRatio="none"` +
// `non-scaling-stroke` o tracejado da animação saía cortado.
const ESPACO_VERTICAL = 130
const MARGEM_TOPO = 70
const LARGURA_MAXIMA = 720

/** Zigue-zague de cima para baixo, como o caminho do mobile. */
function posicoes(total: number, largura: number): Ponto[] {
  const centro = largura / 2
  const amplitude = Math.min(160, largura * 0.24)
  return Array.from({ length: total }, (_, i) => ({
    x: centro + amplitude * Math.sin((Math.PI / 2) * i - Math.PI / 2),
    y: MARGEM_TOPO + i * ESPACO_VERTICAL,
  }))
}

/** Curva suave passando por todos os pontos (Catmull-Rom convertido em Bézier). */
function caminho(pontos: Ponto[]) {
  if (pontos.length === 0) return ''
  let d = `M ${pontos[0].x} ${pontos[0].y}`
  for (let i = 0; i < pontos.length - 1; i++) {
    const p0 = pontos[i - 1] ?? pontos[i]
    const p1 = pontos[i]
    const p2 = pontos[i + 1]
    const p3 = pontos[i + 2] ?? p2
    const c1 = { x: p1.x + (p2.x - p0.x) / 6, y: p1.y + (p2.y - p0.y) / 6 }
    const c2 = { x: p2.x - (p3.x - p1.x) / 6, y: p2.y - (p3.y - p1.y) / 6 }
    d += ` C ${c1.x} ${c1.y}, ${c2.x} ${c2.y}, ${p2.x} ${p2.y}`
  }
  return d
}

const corNumero = {
  concluido: 'text-success',
  atual: 'text-primary',
  bloqueado: 'text-periodo-8',
} as const

function NoModulo({
  modulo,
  ponto,
  numeroAEsquerda,
  selecionado,
  onSelecionar,
}: {
  modulo: ModuloTrilha
  ponto: Ponto
  numeroAEsquerda: boolean
  selecionado: boolean
  onSelecionar: () => void
}) {
  const [escopo, animar] = useAnimate()
  const atual = modulo.status === 'atual'
  const bloqueado = modulo.status === 'bloqueado'

  function clicar() {
    onSelecionar()
    if (bloqueado) animar(escopo.current, { x: [0, -6, 6, -4, 4, 0] }, { duration: 0.4 })
  }

  return (
    // Centralizado pelo `x`/`y` do Framer: ele grava o próprio `transform` ao
    // animar a escala, o que apagaria um `-translate-x-1/2` do Tailwind.
    <motion.div
      className="absolute"
      style={{ left: ponto.x, top: ponto.y, x: '-50%', y: '-50%' }}
      initial={{ scale: 0, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{
        delay: 0.15 + modulo.ordem * 0.05,
        type: 'spring',
        stiffness: 260,
        damping: 18,
      }}
    >
      <span
        aria-hidden
        className={cn(
          'absolute top-1/2 -translate-y-1/2 font-display text-4xl font-extrabold',
          corNumero[modulo.status],
          numeroAEsquerda ? 'right-full mr-3' : 'left-full ml-3',
        )}
      >
        {modulo.ordem}
      </span>

      {/* Sombra no fundo do mar, como uma pedra sob o nó. */}
      <span
        aria-hidden
        className="absolute -bottom-2 left-1/2 h-2 w-3/4 -translate-x-1/2 rounded-full bg-foreground/10 blur-[3px]"
      />

      {/*
        Pulso em dois anéis defasados em meio ciclo: enquanto um some o outro
        já está saindo, então não há pausa visível entre as repetições. Cada
        anel nasce transparente e só depois aparece; se nascesse já visível,
        ele "saltaria" de volta para a borda a cada recomeço.
      */}
      {atual &&
        [0, 1].map((i) => (
          <motion.span
            key={i}
            aria-hidden
            className="absolute inset-0 rounded-full border-4 border-primary"
            initial={{ scale: 1, opacity: 0 }}
            animate={{ scale: [1, 1.6], opacity: [0, 0.6, 0] }}
            transition={{
              duration: 2,
              repeat: Infinity,
              delay: i,
              ease: 'easeOut',
              opacity: { duration: 2, repeat: Infinity, delay: i, times: [0, 0.2, 1] },
            }}
          />
        ))}

      <button
        ref={escopo}
        type="button"
        onClick={clicar}
        aria-pressed={selecionado}
        aria-label={`Módulo ${modulo.ordem}: ${modulo.titulo}${
          bloqueado ? ' (bloqueado)' : modulo.status === 'concluido' ? ' (concluído)' : ''
        }`}
        className={cn(
          'relative flex items-center justify-center rounded-full border-4 shadow-md transition-transform hover:scale-110',
          atual ? 'size-20' : 'size-16',
          modulo.status === 'concluido' && 'border-success/40 bg-success text-success-foreground',
          atual && 'border-card bg-primary text-primary-foreground',
          bloqueado && 'border-border bg-muted text-locked',
          // Seleção na cor do próprio nó, sem o offset branco que virava halo
          // sobre o fundo do mar.
          selecionado && modulo.status === 'concluido' && 'ring-4 ring-success/35',
          selecionado && atual && 'ring-4 ring-primary/35',
          selecionado && bloqueado && 'ring-4 ring-locked/40',
        )}
      >
        {modulo.status === 'concluido' && <Check className="size-7" strokeWidth={3} />}
        {atual && <Play className="ml-1 size-9 fill-current" />}
        {bloqueado && <Lock className="size-6" />}
      </button>
    </motion.div>
  )
}

export function MapaTrilha({
  modulos,
  selecionado,
  onSelecionar,
}: {
  modulos: ModuloTrilha[]
  selecionado: number
  onSelecionar: (ordem: number) => void
}) {
  const rolagemRef = useRef<HTMLDivElement>(null)
  const [largura, setLargura] = useState(LARGURA_MAXIMA)

  // A largura do zigue-zague acompanha a coluna, até um limite.
  useLayoutEffect(() => {
    const elemento = rolagemRef.current
    if (!elemento) return
    const observador = new ResizeObserver(([entrada]) =>
      setLargura(Math.min(entrada.contentRect.width, LARGURA_MAXIMA)),
    )
    observador.observe(elemento)
    return () => observador.disconnect()
  }, [])

  const pontos = posicoes(modulos.length, largura)
  const centro = largura / 2
  const altura = MARGEM_TOPO * 2 + (modulos.length - 1) * ESPACO_VERTICAL
  const indiceAtual = modulos.findIndex((m) => m.status === 'atual')
  const terminou = modulos.length > 0 && modulos.every((m) => m.status === 'concluido')
  // Onde o polvo fica: no módulo atual, ou no último quando a trilha acabou.
  const indicePolvo = terminou ? modulos.length - 1 : indiceAtual
  const pontoPolvo = indicePolvo >= 0 ? pontos[indicePolvo] : null
  // Até onde o caminho já foi percorrido (-1: nada, trilha bloqueada).
  const fimPercorrido = terminou ? modulos.length - 1 : indiceAtual
  // Verde sólido no que já foi feito; pontilhado só no que falta, para os
  // pontinhos não aparecerem por baixo do trecho concluído.
  const percorrido = fimPercorrido > 0 ? caminho(pontos.slice(0, fimPercorrido + 1)) : ''
  const restante = terminou ? '' : caminho(pontos.slice(Math.max(fimPercorrido, 0)))
  // O polvo vai para o lado com mais espaço: o do centro do mapa.
  const ladoDireito = pontoPolvo ? pontoPolvo.x <= centro : true

  // Ao abrir, rola até o módulo em que o aluno parou.
  useEffect(() => {
    const elemento = rolagemRef.current
    if (!elemento || !pontoPolvo) return
    elemento.scrollTo({ top: pontoPolvo.y - elemento.clientHeight / 2, behavior: 'smooth' })
    // Só na montagem.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div ref={rolagemRef} className="relative h-full overflow-y-auto overflow-x-hidden">
      <div className="relative mx-auto" style={{ width: largura, height: altura }}>
        <svg width={largura} height={altura} className="absolute inset-0" aria-hidden>
          {restante && (
            <path
              d={restante}
              fill="none"
              className="stroke-card"
              strokeWidth={8}
              strokeLinecap="round"
              strokeDasharray="1 18"
            />
          )}
          {percorrido && (
            <>
              {/* Brilho largo por baixo do traço. */}
              <motion.path
                d={percorrido}
                fill="none"
                className="stroke-success/25"
                strokeWidth={22}
                strokeLinecap="round"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ delay: 0.3, duration: 1.2, ease: 'easeInOut' }}
              />
              <motion.path
                d={percorrido}
                fill="none"
                className="stroke-success"
                strokeWidth={8}
                strokeLinecap="round"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ delay: 0.3, duration: 1.2, ease: 'easeInOut' }}
              />
            </>
          )}
        </svg>

        {modulos.map((modulo, i) => (
          <NoModulo
            key={modulo.id}
            modulo={modulo}
            ponto={pontos[i]}
            // Número do lado de fora do zigue-zague, longe do polvo.
            numeroAEsquerda={pontos[i].x <= centro}
            selecionado={modulo.ordem === selecionado}
            onSelecionar={() => onSelecionar(modulo.ordem)}
          />
        ))}

        {/* O polvo acompanha o aluno: fica ao lado do módulo atual. */}
        {pontoPolvo && (
          <motion.div
            className="pointer-events-none absolute"
            style={{
              left: pontoPolvo.x,
              top: pontoPolvo.y,
              x: ladoDireito ? '3.5rem' : 'calc(-100% - 3.5rem)',
              y: '-55%',
            }}
            initial={{ opacity: 0, scale: 0.6 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.7, type: 'spring' }}
          >
            {/* Bolhinhas saindo do polvo. */}
            {[0, 1, 2].map((i) => (
              <motion.span
                key={i}
                aria-hidden
                className="absolute rounded-full border-2 border-card bg-card/40"
                style={{ left: `${40 + i * 12}%`, width: 8 + i * 3, height: 8 + i * 3 }}
                initial={{ top: '10%', opacity: 0 }}
                animate={{ top: '-30%', opacity: [0, 1, 0] }}
                transition={{ duration: 2.4, repeat: Infinity, delay: i * 0.8, ease: 'easeOut' }}
              />
            ))}
            <motion.img
              src={mascotePolvo}
              alt=""
              draggable={false}
              className="h-36 select-none drop-shadow-lg"
              animate={
                terminou
                  ? { rotate: [0, -12, 12, -12, 0], y: [0, -16, 0] }
                  : { y: [0, -10, 0], rotate: [0, -3, 3, 0] }
              }
              transition={{ duration: terminou ? 1.4 : 3.5, repeat: Infinity, ease: 'easeInOut' }}
            />
            {/* Sombra no "chão", encolhendo quando o polvo sobe. */}
            <motion.span
              aria-hidden
              className="absolute -bottom-2 left-1/2 h-3 w-24 rounded-full bg-foreground/15 blur-sm"
              style={{ x: '-50%' }}
              animate={{ scaleX: [1, 0.8, 1], opacity: [0.8, 0.5, 0.8] }}
              transition={{ duration: terminou ? 1.4 : 3.5, repeat: Infinity, ease: 'easeInOut' }}
            />
          </motion.div>
        )}
      </div>
    </div>
  )
}
