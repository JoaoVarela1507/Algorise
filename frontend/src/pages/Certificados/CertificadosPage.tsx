import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowLeft, ArrowRight, Award, Hourglass, Info, Lock } from 'lucide-react'
import { PERIODOS, coresPeriodo } from '@/components/trilhas/periodos'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/contexts/AuthContext'
import { cn } from '@/lib/utils'
import { trilhasMock } from '@/mocks/trilhas'
import type { TrilhaResumo } from '@/types/trilha'
import mascotePolvo from '@/assets/images/mascote-polvo.png'

/**
 * Certificados emitidos pelos parceiros. Ainda não há rota que liste os do
 * aluno, então a lista começa vazia e cada trilha aparece como um certificado
 * a conquistar.
 */
const certificadosEmitidos: { trilhaId: string }[] = []

function ItemCertificado({ trilha, indice }: { trilha: TrilhaResumo; indice: number }) {
  const concluida = trilha.modulosConcluidos >= trilha.totalModulos
  const progresso = Math.round((trilha.modulosConcluidos / trilha.totalModulos) * 100)

  return (
    <motion.li
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: indice * 0.06 }}
    >
      <Link
        to="/trilhas"
        className="group flex items-center gap-4 rounded-lg border border-border bg-card p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/50 hover:shadow-md"
      >
        <span
          className="flex size-12 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary"
          title="Parceiro do Algorise"
        >
          <Award className="size-6" aria-hidden />
        </span>

        <div className="min-w-0 flex-1">
          <p className="truncate font-display text-lg font-bold text-foreground">{trilha.nome}</p>
          {concluida ? (
            <p className="flex items-center gap-1.5 text-sm font-semibold text-success">
              <Hourglass className="size-3.5" aria-hidden />
              Trilha concluída · aguardando emissão pelo parceiro
            </p>
          ) : (
            <div className="mt-1 flex items-center gap-3">
              <div className="h-2 max-w-48 flex-1 overflow-hidden rounded-full bg-muted">
                <motion.div
                  className="h-full rounded-full bg-success"
                  initial={{ width: 0 }}
                  animate={{ width: `${progresso}%` }}
                  transition={{ delay: 0.3 + indice * 0.06, duration: 0.6 }}
                />
              </div>
              <span className="text-xs font-bold text-muted-foreground">
                {trilha.modulosConcluidos}/{trilha.totalModulos} módulos
              </span>
            </div>
          )}
        </div>

        <span
          className="flex size-11 shrink-0 items-center justify-center rounded-full bg-muted text-locked transition-transform group-hover:scale-110"
          aria-label="Certificado bloqueado"
        >
          <Lock className="size-5" />
        </span>
      </Link>
    </motion.li>
  )
}

export function CertificadosPage() {
  const { usuario } = useAuth()
  const navigate = useNavigate()

  const periodosComTrilha = PERIODOS.filter((p) => trilhasMock.some((t) => t.periodo === p))
  const [periodo, setPeriodo] = useState<number>(() =>
    usuario?.periodo && periodosComTrilha.includes(usuario.periodo as (typeof PERIODOS)[number])
      ? usuario.periodo
      : (periodosComTrilha[0] ?? 1),
  )
  const doPeriodo = trilhasMock.filter((t) => t.periodo === periodo)
  const total = trilhasMock.length

  return (
    <div className="flex min-h-full flex-col gap-6">
      <header className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)} aria-label="Voltar">
          <ArrowLeft />
        </Button>
        <div>
          <h1 className="font-display text-3xl font-bold text-foreground">Certificados</h1>
          <p className="text-muted-foreground">
            Certificações de parceiros de mercado por trilha concluída.
          </p>
        </div>
      </header>

      <div className="grid flex-1 gap-6 xl:grid-cols-3">
        {/* Estado vazio: nenhum certificado ainda. */}
        <motion.section
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col gap-5 rounded-lg border border-border bg-card p-6 shadow-sm"
        >
          <div className="flex flex-1 flex-col items-center justify-center gap-4 text-center">
            <div className="relative">
              <motion.img
                src={mascotePolvo}
                alt=""
                className="h-32 select-none"
                draggable={false}
                animate={{ y: [0, -8, 0] }}
                transition={{ duration: 3.5, repeat: Infinity, ease: 'easeInOut' }}
              />
              <motion.span
                className="absolute -bottom-2 -right-4 flex size-14 items-center justify-center rounded-full border-4 border-card bg-muted text-locked shadow"
                animate={{ rotate: [0, -10, 10, 0] }}
                transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
                aria-hidden
              >
                <Award className="size-7" />
              </motion.span>
            </div>

            <div>
              <p className="font-display text-5xl font-extrabold text-foreground">
                {certificadosEmitidos.length}
                <span className="text-2xl text-muted-foreground"> de {total}</span>
              </p>
              <p className="text-sm font-semibold text-muted-foreground">
                certificados conquistados
              </p>
            </div>

            <div>
              <h2 className="font-display text-xl font-bold text-foreground">
                Você ainda não tem certificados
              </h2>
              <p className="mx-auto max-w-xs text-muted-foreground">
                Conclua todos os módulos de uma trilha para liberar o certificado do parceiro.
              </p>
            </div>

            <Button asChild size="lg" className="group">
              <Link to="/trilhas">
                Ir para as trilhas
                <ArrowRight className="transition-transform group-hover:translate-x-1" />
              </Link>
            </Button>
          </div>

          <p className="flex gap-2 rounded-lg bg-secondary/60 p-4 text-sm text-muted-foreground">
            <Info className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
            Aqui você encontra os certificados dos cursos oferecidos pelos parceiros do Algorise com
            base na sua ementa. Certificados de outras instituições ou cursos não parceiros não são
            exibidos nesta página.
          </p>
        </motion.section>

        {/* Certificados a conquistar, por período. */}
        <motion.section
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="flex flex-col rounded-lg border border-border bg-card p-6 shadow-sm xl:col-span-2"
        >
          <h2 className="font-display text-xl font-bold text-foreground">Veja seus certificados</h2>
          <p className="mb-4 text-sm text-muted-foreground">
            Cada trilha concluída libera um certificado. Escolha o período:
          </p>

          <div className="mb-5 flex flex-wrap gap-2" role="tablist" aria-label="Período">
            {periodosComTrilha.map((p) => {
              const ativo = p === periodo
              return (
                <button
                  key={p}
                  type="button"
                  role="tab"
                  aria-selected={ativo}
                  onClick={() => setPeriodo(p)}
                  className={cn(
                    'flex items-center gap-2 rounded-full border-2 py-1.5 pl-3 pr-4 text-sm font-bold transition-colors',
                    coresPeriodo[p].borda,
                    ativo
                      ? cn(coresPeriodo[p].cheio, 'text-periodo-foreground shadow-md')
                      : 'bg-card text-foreground hover:shadow-sm',
                  )}
                >
                  <span
                    className={cn(
                      'size-2.5 rounded-full',
                      ativo ? 'bg-card' : coresPeriodo[p].cheio,
                    )}
                    aria-hidden
                  />
                  {p}º Período
                </button>
              )
            })}
          </div>

          <div
            className={cn(
              'flex-1 rounded-lg border-2 p-4',
              coresPeriodo[periodo]?.borda,
              coresPeriodo[periodo]?.suave,
            )}
          >
            <AnimatePresence mode="wait">
              <motion.ol
                key={periodo}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
                className="flex flex-col gap-3"
              >
                {doPeriodo.map((trilha, i) => (
                  <ItemCertificado key={trilha.id} trilha={trilha} indice={i} />
                ))}
              </motion.ol>
            </AnimatePresence>
          </div>
        </motion.section>
      </div>
    </div>
  )
}
