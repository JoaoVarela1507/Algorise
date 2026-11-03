import { CheckCircle2, Clock, Hourglass, Lightbulb } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import type { Correcao } from '@/hooks/useAtividades'
import { cn } from '@/lib/utils'

/**
 * O que toda atividade tem em volta do exercício (telas 28 a 34): progresso no
 * passo, tempo sugerido, enunciado, dica e o "Avançar" que só libera depois da
 * correção do servidor. O exercício em si (terminal, alternativas, lacunas…)
 * entra como `children`.
 */

/** Erros seguidos até a dica abrir sozinha: depois disso, insistir sem ela só frustra. */
const ERROS_ATE_A_DICA = 2

export interface MolduraAtividadeProps {
  numero: number
  total: number
  enunciado: string
  dica?: string | null
  /** Trecho de código mostrado junto do enunciado (a múltipla escolha usa). */
  codigo?: string | null
  tempoSugeridoSegundos?: number | null
  correcao: Correcao
  /** O que dizer antes da primeira tentativa. */
  instrucao: string
  /** Texto do acerto; sem ele, vale o feedback do servidor. */
  mensagemDeAcerto?: string
  /** Por que o Avançar não responde, para leitor de tela. */
  porQueBloqueado: string
  /** Atividade sem correção automática: o Avançar já nasce liberado. */
  semCorrecao?: boolean
  aoAvancar: () => void
  children: ReactNode
}

export function MolduraAtividade({
  numero,
  total,
  enunciado,
  dica,
  codigo,
  tempoSugeridoSegundos,
  correcao,
  instrucao,
  mensagemDeAcerto,
  porQueBloqueado,
  semCorrecao = false,
  aoAvancar,
  children,
}: MolduraAtividadeProps) {
  const [pediuDica, setPediuDica] = useState(false)
  const { estado, tentativas, feedback } = correcao
  const liberado = semCorrecao || estado === 'certa' || estado === 'em-analise'
  const mostrarDica = pediuDica || tentativas >= ERROS_ATE_A_DICA
  const idPorQue = `por-que-bloqueado-${numero}`

  return (
    <section className="flex flex-col gap-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Progresso numero={numero} total={total} />
          <span className="text-sm font-bold text-muted-foreground">
            Atividade {numero} de {total}
          </span>
        </div>
        {tempoSugeridoSegundos ? (
          <Cronometro segundos={tempoSugeridoSegundos} parado={liberado} />
        ) : null}
      </header>

      <h2 className="font-display text-xl font-bold text-foreground">{enunciado}</h2>

      {codigo ? <BlocoDeCodigo codigo={codigo} /> : null}

      {dica ? (
        <div>
          <Button variant="ghost" size="sm" onClick={() => setPediuDica(!mostrarDica)}>
            <Lightbulb className="size-4" aria-hidden />
            {mostrarDica ? 'Esconder dica' : 'Ver dica'}
          </Button>
          {mostrarDica && <p className="mt-1 text-sm text-muted-foreground">{dica}</p>}
        </div>
      ) : null}

      {children}

      <footer className="flex flex-wrap items-center justify-between gap-3">
        <Situacao
          estado={semCorrecao ? 'sem-correcao' : estado}
          tentativas={tentativas}
          feedback={feedback}
          instrucao={instrucao}
          mensagemDeAcerto={mensagemDeAcerto}
        />

        <Button
          size="lg"
          disabled={!liberado || correcao.enviando}
          onClick={aoAvancar}
          // O botão desabilitado some do leitor de tela; o texto ao lado diz o
          // que falta, e isto explica o porquê de ele não responder.
          aria-describedby={liberado ? undefined : idPorQue}
        >
          Avançar
        </Button>
        {!liberado && (
          <span id={idPorQue} className="sr-only">
            {porQueBloqueado}
          </span>
        )}
      </footer>
    </section>
  )
}

function Situacao({
  estado,
  tentativas,
  feedback,
  instrucao,
  mensagemDeAcerto,
}: {
  estado: Correcao['estado'] | 'sem-correcao'
  tentativas: number
  feedback: string | null
  instrucao: string
  mensagemDeAcerto?: string
}) {
  if (estado === 'certa') {
    return (
      <p className="flex items-center gap-2 text-sm font-bold text-success" role="status">
        <CheckCircle2 className="size-5" aria-hidden />
        {mensagemDeAcerto ?? feedback ?? 'Resposta certa!'}
      </p>
    )
  }
  if (estado === 'em-analise') {
    return (
      <p className="flex items-center gap-2 text-sm font-semibold text-foreground" role="status">
        <EmAnalise />
        <span>
          {feedback ?? 'Resposta recebida.'}
          <Reticencias />
        </span>
      </p>
    )
  }
  if (estado === 'sem-correcao') {
    return <p className="text-sm text-muted-foreground">{instrucao}</p>
  }
  if (estado === 'errada') {
    return (
      <div className="text-sm" role="status">
        <p className="text-muted-foreground">Não foi dessa vez. Tentativas: {tentativas}.</p>
        {feedback && <p className="font-semibold text-foreground">{feedback}</p>}
      </div>
    )
  }
  return <p className="text-sm text-muted-foreground">{instrucao}</p>
}

/**
 * Ampulheta que vira, como a de verdade: gira meia volta e espera a areia
 * descer. Com "reduzir animações" ligado, o `MotionConfig` do App a deixa parada.
 */
function EmAnalise() {
  return (
    <span className="relative flex size-7 shrink-0 items-center justify-center" aria-hidden>
      <motion.span
        className="absolute inset-0 rounded-full bg-primary/15"
        animate={{ scale: [1, 1.25, 1], opacity: [0.6, 0, 0.6] }}
        transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.span
        className="relative text-primary"
        animate={{ rotate: [0, 180, 180, 360, 360] }}
        transition={{
          duration: 2.4,
          repeat: Infinity,
          ease: 'easeInOut',
          times: [0, 0.2, 0.5, 0.7, 1],
        }}
      >
        <Hourglass className="size-5" />
      </motion.span>
    </span>
  )
}

/** Três pontinhos acendendo em sequência, de "ainda está trabalhando". */
function Reticencias() {
  return (
    <span className="ml-0.5 inline-flex gap-0.5" aria-hidden>
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="inline-block size-1 rounded-full bg-current"
          animate={{ opacity: [0.2, 1, 0.2], y: [0, -2, 0] }}
          transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2, ease: 'easeInOut' }}
        />
      ))}
    </span>
  )
}

export function BlocoDeCodigo({ codigo, className }: { codigo: string; className?: string }) {
  return (
    <pre
      className={cn(
        'overflow-x-auto rounded-lg border border-border bg-[#11161d] p-4 font-mono text-sm text-[#e6edf3]',
        className,
      )}
    >
      <code>{codigo}</code>
    </pre>
  )
}

function Progresso({ numero, total }: { numero: number; total: number }) {
  return (
    <div
      className="flex gap-1"
      role="progressbar"
      aria-valuenow={numero}
      aria-valuemin={1}
      aria-valuemax={total}
      aria-label={`Atividade ${numero} de ${total}`}
    >
      {Array.from({ length: total }, (_, indice) => (
        <span
          key={indice}
          className={cn(
            'h-2 w-8 rounded-full transition-colors',
            indice < numero ? 'bg-primary' : 'bg-muted',
          )}
        />
      ))}
    </div>
  )
}

/**
 * Tempo sugerido, contando para trás.
 *
 * Chegar a zero não bloqueia nem reprova: a atividade não é prova, e um
 * cronômetro que trava a tela só serviria para desistir. Ele vira um aviso.
 */
function Cronometro({ segundos, parado }: { segundos: number; parado: boolean }) {
  const [restante, setRestante] = useState(segundos)

  useEffect(() => {
    if (parado) return
    const id = setInterval(() => setRestante((atual) => Math.max(atual - 1, 0)), 1000)
    return () => clearInterval(id)
  }, [parado])

  const estourou = restante === 0

  return (
    <p
      className={cn(
        'flex items-center gap-1.5 text-sm font-bold',
        estourou ? 'text-streak' : 'text-muted-foreground',
      )}
      // `off`: o cronômetro mudando a cada segundo atropelaria o leitor de tela.
      aria-live="off"
    >
      <Clock className="size-4" aria-hidden />
      {estourou ? 'Sem pressa, continue' : `${formatar(restante)} sugeridos`}
    </p>
  )
}

function formatar(segundos: number): string {
  const minutos = Math.floor(segundos / 60)
  const resto = segundos % 60
  return `${minutos}:${String(resto).padStart(2, '0')}`
}
