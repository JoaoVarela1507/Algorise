import { useEffect, useRef } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { RotateCcw, Star, Trophy } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { ExecucaoApi, ResultadoDoCasoApi } from '@/services/desafios'
import { useAccessibilityStore } from '@/stores/useAccessibilityStore'
import mascotePolvo from '@/assets/images/mascote-polvo.png'

/**
 * O veredito do desafio (telas 41 e 42): o polvo comemorando com o XP, ou
 * preocupado com o "Tente novamente!" e o que deu errado. Abre por cima do
 * editor, como o fechamento de passo, e o código continua lá ao voltar.
 */

const MOTIVOS: Record<string, string> = {
  tempo_esgotado: 'Seu programa demorou demais. Será que algum laço nunca termina?',
  memoria_estourada: 'Seu programa usou memória demais.',
  saida_grande_demais: 'Seu programa escreveu coisa demais na tela.',
  erro_de_execucao: 'Seu programa deu erro ao rodar.',
  saida_diferente: 'O programa rodou, mas a saída não é a esperada.',
}

const CORES = ['bg-primary', 'bg-xp', 'bg-success', 'bg-periodo-2', 'bg-periodo-7', 'bg-streak']
const CONFETES = Array.from({ length: 20 }, (_, i) => {
  const angulo = (i / 20) * Math.PI * 2
  return {
    x: Math.cos(angulo) * (130 + (i % 3) * 40),
    y: Math.sin(angulo) * 100 - 50,
    cor: CORES[i % CORES.length],
  }
})

export function ResultadoDoDesafio({
  execucao,
  xp,
  jaTinhaFeito,
  aoTentarDeNovo,
  aoVoltarParaTrilhas,
}: {
  execucao: ExecucaoApi
  /** XP do desafio: só aparece no primeiro acerto, que é o único que paga. */
  xp: number
  jaTinhaFeito: boolean
  /** Fecha e volta ao editor ("Voltar para Desafio"). */
  aoTentarDeNovo: () => void
  aoVoltarParaTrilhas: () => void
}) {
  const doSistema = useReducedMotion()
  const doAluno = useAccessibilityStore((estado) => estado.reduzirAnimacoes)
  const parado = Boolean(doSistema) || doAluno
  const botao = useRef<HTMLButtonElement>(null)
  useEffect(() => botao.current?.focus(), [])

  const passou = execucao.aprovada
  // A sandbox não rodou: não é culpa do código, então nada de "tente de novo".
  const foraDoAr = execucao.status === 'falhou'
  const falhou = execucao.casos.find((caso) => !caso.passou)

  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 p-4 backdrop-blur-sm"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="resultado-desafio-titulo"
      onKeyDown={(evento) => evento.key === 'Escape' && aoTentarDeNovo()}
    >
      <motion.div
        className={cn(
          'relative max-h-full w-full max-w-md overflow-y-auto rounded-2xl border bg-card p-6 text-center shadow-2xl sm:p-8',
          passou ? 'border-xp/60' : 'border-border',
        )}
        initial={parado ? false : { scale: 0.9, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        transition={{ type: 'spring', stiffness: 300, damping: 22 }}
      >
        {passou && !parado && (
          <div aria-hidden className="pointer-events-none absolute left-1/2 top-24">
            {CONFETES.map((confete, i) => (
              <motion.span
                key={i}
                className={cn('absolute size-2 rounded-sm', confete.cor)}
                initial={{ x: 0, y: 0, opacity: 1 }}
                animate={{ x: confete.x, y: [0, confete.y, confete.y + 180], opacity: [1, 1, 0] }}
                transition={{ duration: 1.8, delay: (i % 4) * 0.04, ease: 'easeOut' }}
              />
            ))}
          </div>
        )}

        <motion.img
          src={mascotePolvo}
          alt=""
          draggable={false}
          className={cn('mx-auto h-28 select-none', !passou && 'grayscale-[35%]')}
          initial={parado ? false : passou ? { y: 20, scale: 0.6 } : { rotate: 0 }}
          animate={
            parado
              ? undefined
              : passou
                ? { y: [20, -16, 0], scale: 1 }
                : { rotate: [0, -10, 8, -5, 0] }
          }
          transition={
            passou
              ? { y: { duration: 0.6, ease: 'easeOut' }, scale: { duration: 0.3 } }
              : { duration: 0.7 }
          }
        />

        <h2
          id="resultado-desafio-titulo"
          className="mt-3 font-display text-3xl font-extrabold text-foreground"
        >
          {passou ? 'Desafio concluído!' : foraDoAr ? 'Não deu para testar' : 'Tente novamente!'}
        </h2>

        {passou ? (
          <Sucesso xp={jaTinhaFeito ? 0 : xp} total={execucao.casos.length} />
        ) : foraDoAr ? (
          <p className="mt-2 text-muted-foreground">
            {execucao.erro ?? 'A correção está fora do ar agora.'} Seu código continua no editor.
          </p>
        ) : (
          <Falha caso={falhou} stderr={execucao.stderr} />
        )}

        <div className="mt-6 flex flex-col gap-2">
          {passou ? (
            <>
              <Button ref={botao} size="lg" full onClick={aoVoltarParaTrilhas}>
                <Trophy />
                Voltar para Trilhas
              </Button>
              <Button variant="ghost" full onClick={aoTentarDeNovo}>
                Ver meu código
              </Button>
            </>
          ) : (
            <>
              <Button ref={botao} size="lg" full onClick={aoTentarDeNovo}>
                <RotateCcw />
                Voltar para Desafio
              </Button>
              <Button variant="ghost" full onClick={aoVoltarParaTrilhas}>
                Voltar para Trilhas
              </Button>
            </>
          )}
        </div>
      </motion.div>
    </motion.div>
  )
}

function Sucesso({ xp, total }: { xp: number; total: number }) {
  return (
    <>
      <p className="mt-2 text-muted-foreground">
        Seu programa passou {total === 1 ? 'no caso de teste' : `nos ${total} casos de teste`}.
        Mandou bem!
      </p>
      {xp > 0 && (
        <p className="mx-auto mt-4 flex w-fit items-center gap-2 rounded-full bg-xp px-4 py-2 font-display text-xl font-extrabold text-foreground shadow">
          <Star className="size-5 fill-current" aria-hidden />+{xp} XP
        </p>
      )}
    </>
  )
}

function Falha({ caso, stderr }: { caso: ResultadoDoCasoApi | undefined; stderr: string }) {
  const motivo = (caso?.motivo && MOTIVOS[caso.motivo]) ?? 'Algum caso de teste não passou.'
  // Do traceback, só a última linha (`ValueError: ...`) diz algo ao aluno.
  const erro = caso?.motivo === 'erro_de_execucao' ? stderr.trim().split('\n').pop() : null

  return (
    <div className="mt-2 flex flex-col gap-3 text-left">
      <p className="text-center text-muted-foreground">{motivo}</p>
      {erro && (
        <pre className="overflow-x-auto rounded-lg bg-muted p-3 font-mono text-xs text-destructive">
          {erro}
        </pre>
      )}
      {caso?.publico ? (
        <dl className="grid grid-cols-[minmax(0,1fr)] gap-2 text-sm">
          <Saida titulo="Entrada" texto={caso.entrada ?? ''} />
          <Saida titulo="Esperado" texto={caso.esperado ?? ''} />
          <Saida titulo="Seu programa mostrou" texto={caso.obtido ?? ''} />
        </dl>
      ) : (
        caso && (
          <p className="text-center text-sm text-foreground">
            Ele passou no exemplo, mas falhou num caso de teste oculto. Teste com outras entradas,
            inclusive as extremas, como uma entrada vazia.
          </p>
        )
      )}
    </div>
  )
}

function Saida({ titulo, texto }: { titulo: string; texto: string }) {
  return (
    <div>
      <dt className="text-xs font-bold uppercase tracking-wide text-muted-foreground">{titulo}</dt>
      <dd>
        <pre className="mt-1 max-h-32 overflow-auto rounded-lg bg-muted p-2 font-mono text-xs text-foreground">
          {texto.replace(/\n+$/, '') || '(vazio)'}
        </pre>
      </dd>
    </div>
  )
}
