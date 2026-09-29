import { useId, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ChevronLeft, Crown, ListOrdered, Star } from 'lucide-react'
import { AvatarIniciais } from '@/components/home/AvatarIniciais'
import { useContagem } from '@/hooks/useContagem'
import { cn } from '@/lib/utils'
import type { PosicaoRanking } from '@/types/ranking'

const formatarXp = new Intl.NumberFormat('pt-BR')

// Ordem visual do pódio: 2º à esquerda, 1º no meio, 3º à direita.
const podio = [
  {
    posicao: 2,
    altura: 'h-28',
    degrau: 'border-locked bg-locked/20',
    anel: 'ring-locked',
    atraso: 0.1,
  },
  { posicao: 1, altura: 'h-40', degrau: 'border-xp bg-xp/25', anel: 'ring-xp', atraso: 0 },
  {
    posicao: 3,
    altura: 'h-20',
    degrau: 'border-streak bg-streak/20',
    anel: 'ring-streak',
    atraso: 0.2,
  },
] as const

function estrelasPorPosicao(posicao: number) {
  if (posicao <= 3) return 3
  if (posicao <= 10) return 2
  return 1
}

function SeuRank({ voce, acima }: { voce: PosicaoRanking; acima?: PosicaoRanking }) {
  const xp = useContagem(voce.xp, { duracao: 1.2, atraso: 0.4 })
  const estrelas = estrelasPorPosicao(voce.posicao)

  return (
    <div className="flex flex-col items-center gap-3 rounded-lg bg-secondary/60 px-6 py-6 text-center">
      <span className="font-display text-lg font-bold text-foreground">Seu rank</span>

      <div className="flex items-end gap-1" aria-label={`${estrelas} de 3 estrelas`} role="img">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            initial={{ scale: 0, rotate: -45 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ delay: 0.3 + i * 0.12, type: 'spring', stiffness: 300, damping: 12 }}
            className={cn(i === 1 && '-translate-y-2')}
          >
            <Star
              className={cn(
                i === 1 ? 'size-12' : 'size-9',
                i < estrelas ? 'fill-xp text-xp' : 'fill-muted text-locked',
              )}
            />
          </motion.span>
        ))}
      </div>

      <motion.div
        initial={{ scale: 0.6, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: 0.6, type: 'spring', stiffness: 260, damping: 14 }}
        className="relative"
      >
        {/* Pontas da faixa, desenhadas antes para ficarem atrás dela. */}
        <span
          aria-hidden
          className="absolute -left-3 top-1/2 size-7 -translate-y-1/2 rotate-45 rounded-sm bg-primary/60"
        />
        <span
          aria-hidden
          className="absolute -right-3 top-1/2 size-7 -translate-y-1/2 rotate-45 rounded-sm bg-primary/60"
        />
        <span className="relative block rounded-md bg-primary px-8 py-1 font-display text-4xl font-extrabold text-primary-foreground shadow-md">
          {voce.posicao}º
        </span>
      </motion.div>

      <p className="font-display text-2xl font-bold text-foreground">
        <span aria-hidden>{formatarXp.format(xp)}</span>
        <span className="sr-only">{formatarXp.format(voce.xp)}</span> XP
      </p>

      {acima && (
        <p className="max-w-[15rem] text-sm text-muted-foreground">
          Faltam{' '}
          <strong className="text-foreground">{formatarXp.format(acima.xp - voce.xp)} XP</strong>{' '}
          para passar {acima.nome.split(' ')[0]}.
        </p>
      )}
    </div>
  )
}

function Podio({ ranking }: { ranking: PosicaoRanking[] }) {
  return (
    <ol className="flex items-end justify-center gap-3" aria-label="Pódio">
      {podio.map((degrau) => {
        const pessoa = ranking.find((p) => p.posicao === degrau.posicao)
        if (!pessoa) return null
        return (
          <li key={degrau.posicao} className="flex w-28 flex-col items-center 2xl:w-32">
            <motion.div
              initial={{ opacity: 0, y: -24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                delay: 0.5 + degrau.atraso,
                type: 'spring',
                stiffness: 300,
                damping: 16,
              }}
              className="mb-2 flex w-full flex-col items-center"
            >
              <div className="relative">
                {degrau.posicao === 1 && (
                  <motion.span
                    className="absolute -top-7 left-1/2 -translate-x-1/2"
                    animate={{ rotate: [-8, 8, -8] }}
                    transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
                  >
                    <Crown className="size-7 fill-xp text-xp" aria-hidden />
                  </motion.span>
                )}
                <AvatarIniciais
                  nome={pessoa.nome}
                  className={cn(
                    'ring-4 ring-offset-2 ring-offset-card',
                    degrau.anel,
                    degrau.posicao === 1 ? 'size-20 text-xl' : 'size-14 text-lg',
                  )}
                />
              </div>
              <span className="mt-2 max-w-full truncate font-bold text-foreground">
                {pessoa.nome.split(' ')[0]}
              </span>
              <span className="text-xs text-muted-foreground">
                {formatarXp.format(pessoa.xp)} XP
              </span>
            </motion.div>

            <motion.div
              initial={{ scaleY: 0 }}
              animate={{ scaleY: 1 }}
              style={{ originY: 1 }}
              transition={{ delay: degrau.atraso, duration: 0.5, ease: 'easeOut' }}
              className={cn(
                'flex w-full justify-center rounded-t-lg border-2 border-b-0 pt-2 font-display text-4xl font-extrabold text-foreground',
                degrau.altura,
                degrau.degrau,
              )}
            >
              <span className="sr-only">Posição</span>
              {degrau.posicao}
            </motion.div>
          </li>
        )
      })}
    </ol>
  )
}

function ListaRanking({
  ranking,
  usuarioAtualId,
}: {
  ranking: PosicaoRanking[]
  usuarioAtualId: string
}) {
  return (
    <ol className="flex flex-col gap-1">
      {ranking.map((pessoa, i) => {
        const ehVoce = pessoa.usuarioId === usuarioAtualId
        return (
          <motion.li
            key={pessoa.usuarioId}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.04 }}
            className={cn(
              'flex items-center gap-3 rounded-lg px-3 py-2',
              ehVoce ? 'bg-primary/10 ring-1 ring-primary/40' : 'hover:bg-muted/60',
            )}
            aria-current={ehVoce || undefined}
          >
            <span className="w-6 text-center font-display font-bold text-muted-foreground">
              {pessoa.posicao <= 3 ? (
                <Crown
                  className={cn(
                    'mx-auto size-4',
                    pessoa.posicao === 1 && 'fill-xp text-xp',
                    pessoa.posicao === 2 && 'fill-locked text-locked',
                    pessoa.posicao === 3 && 'fill-streak text-streak',
                  )}
                  aria-label={`${pessoa.posicao}º`}
                />
              ) : (
                pessoa.posicao
              )}
            </span>
            <AvatarIniciais nome={pessoa.nome} className="size-9 text-xs" />
            <span className="flex-1 truncate font-semibold text-foreground">{pessoa.nome}</span>
            <span className="text-sm font-bold text-foreground">
              {formatarXp.format(pessoa.xp)} XP
            </span>
          </motion.li>
        )
      })}
    </ol>
  )
}

export function RankingCard({
  ranking,
  usuarioAtualId,
  className,
}: {
  ranking: PosicaoRanking[]
  usuarioAtualId: string
  className?: string
}) {
  const [verLista, setVerLista] = useState(false)
  const conteudoId = useId()
  const voce = ranking.find((p) => p.usuarioId === usuarioAtualId)
  const acima = voce && ranking.find((p) => p.posicao === voce.posicao - 1)

  return (
    <div
      className={cn(
        'flex flex-col rounded-lg border border-border bg-card p-6 shadow-sm',
        className,
      )}
    >
      <h2 className="text-center font-display text-xl text-foreground">
        Sua <strong>posição</strong> no ranking da <strong>Trilha</strong>
      </h2>

      {/*
        O pódio e a lista completa se revezam no mesmo espaço, então abrir o
        ranking não muda a altura do card nem empurra o resto da tela.
      */}
      <div id={conteudoId} className="mt-4 flex min-h-0 flex-1 flex-col justify-center">
        <AnimatePresence mode="wait" initial={false}>
          {verLista ? (
            <motion.div
              key="lista"
              initial={{ opacity: 0, x: 24 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 24 }}
              transition={{ duration: 0.25 }}
              className="max-h-[26rem] overflow-y-auto pr-1"
            >
              <ListaRanking ranking={ranking} usuarioAtualId={usuarioAtualId} />
            </motion.div>
          ) : (
            <motion.div
              key="podio"
              initial={{ opacity: 0, x: -24 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -24 }}
              transition={{ duration: 0.25 }}
              className="grid items-end gap-6 sm:grid-cols-[auto_1fr] xl:grid-cols-1 2xl:grid-cols-[auto_1fr]"
            >
              {voce ? (
                <SeuRank voce={voce} acima={acima} />
              ) : (
                <p className="rounded-lg bg-secondary/60 p-5 text-center text-sm text-muted-foreground">
                  Conclua um módulo para entrar no ranking.
                </p>
              )}
              <Podio ranking={ranking} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <button
        type="button"
        onClick={() => setVerLista((atual) => !atual)}
        aria-expanded={verLista}
        aria-controls={conteudoId}
        className="mx-auto mt-4 flex items-center gap-2 rounded-full px-4 py-1.5 text-sm font-bold text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
      >
        {verLista ? (
          <>
            <ChevronLeft className="size-4" />
            Voltar ao pódio
          </>
        ) : (
          <>
            <ListOrdered className="size-4" />
            Ver ranking completo
          </>
        )}
      </button>
    </div>
  )
}
