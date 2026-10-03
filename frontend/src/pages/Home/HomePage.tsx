import { motion, type Variants } from 'framer-motion'
import { ConquistasCard } from '@/components/home/ConquistasCard'
import { MetaDiariaCard } from '@/components/home/MetaDiariaCard'
import { RankingCard } from '@/components/home/RankingCard'
import { SaudacaoCard } from '@/components/home/SaudacaoCard'
import { StreakCard } from '@/components/home/StreakCard'
import { TrilhaAtualCard } from '@/components/home/TrilhaAtualCard'
import { Carregando, ErroAoCarregar } from '@/components/ui/estados'
import { useAuth } from '@/contexts/AuthContext'
import { useRanking } from '@/hooks/useRanking'
import { conquistasMock, metaDiariaMock, trilhaAtualMock } from '@/mocks/home'

const container: Variants = {
  oculto: {},
  visivel: { transition: { staggerChildren: 0.08 } },
}

const secao: Variants = {
  oculto: { opacity: 0, y: 16 },
  visivel: { opacity: 1, y: 0, transition: { duration: 0.4, ease: 'easeOut' } },
}

export function HomePage() {
  const { usuario } = useAuth()
  // `usuario_id` para a API devolver a posição do aluno mesmo quando ela cai
  // fora da primeira página.
  const ranking = useRanking({ limite: 8, usuarioId: Number(usuario?.id) || undefined })

  return (
    <>
      <motion.div
        variants={container}
        initial="oculto"
        animate="visivel"
        className="flex min-h-full flex-col gap-6"
      >
        <motion.section variants={secao}>
          <SaudacaoCard nome={usuario?.nome ?? 'estudante'} />
        </motion.section>

        {/*
          No desktop são três colunas que preenchem a altura da tela (sem
          scroll): ranking | trilha + conquistas | streak + meta. Os cards
          esticam com h-full e distribuem o conteúdo por dentro. Em telas
          menores tudo empilha e a página rola normalmente.
        */}
        <div className="grid flex-1 gap-6 md:grid-cols-2 xl:grid-cols-12">
          <motion.section variants={secao} className="md:col-span-2 xl:col-span-5">
            {ranking.isPending ? (
              <Carregando rotulo="Carregando ranking…" />
            ) : ranking.isError ? (
              <ErroAoCarregar erro={ranking.error} aoTentarDeNovo={() => void ranking.refetch()} />
            ) : (
              <RankingCard
                ranking={ranking.data.linhas}
                usuarioAtualId={usuario?.id ?? ''}
                className="h-full"
              />
            )}
          </motion.section>

          <div className="flex flex-col gap-6 xl:col-span-4">
            <motion.section variants={secao}>
              <TrilhaAtualCard trilha={trilhaAtualMock} />
            </motion.section>
            <motion.section variants={secao} className="flex-1">
              <ConquistasCard conquistas={conquistasMock} className="h-full" />
            </motion.section>
          </div>

          <div className="flex flex-col gap-6 xl:col-span-3">
            <motion.section variants={secao}>
              <StreakCard dias={usuario?.streakDias ?? 0} />
            </motion.section>
            <motion.section variants={secao} className="flex-1">
              <MetaDiariaCard meta={metaDiariaMock} className="h-full" />
            </motion.section>
          </div>
        </div>
      </motion.div>
    </>
  )
}
