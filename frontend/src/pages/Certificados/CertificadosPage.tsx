import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowLeft, ArrowRight, Award, Download, Info, Lock } from 'lucide-react'
import { coresPeriodo } from '@/components/trilhas/periodos'
import { Button } from '@/components/ui/button'
import { Carregando, ErroAoCarregar } from '@/components/ui/estados'
import { useBaixarCertificado, useCertificados } from '@/hooks/useCertificados'
import { useAuthStore } from '@/stores/useAuthStore'
import { cn } from '@/lib/utils'
import type { ItemDeCertificado } from '@/services/certificados'
import mascotePolvo from '@/assets/images/mascote-polvo.png'

/** O período da aba: as optativas, sem período, ficam na aba 0. */
const chaveDoPeriodo = (periodo: number | null | undefined) => periodo ?? 0
const nomeDoPeriodo = (chave: number) => (chave ? `${chave}º Período` : 'Optativas')

function ItemCertificado({ item, indice }: { item: ItemDeCertificado; indice: number }) {
  const baixar = useBaixarCertificado()
  const liberado = item.estado === 'liberado'
  const progresso = item.total_modulos
    ? Math.round((item.concluidos / item.total_modulos) * 100)
    : 0

  return (
    <motion.li
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: indice * 0.06 }}
      className="flex items-center gap-4 rounded-lg border border-border bg-card p-4 shadow-sm"
    >
      <span
        className={cn(
          'flex size-12 shrink-0 items-center justify-center rounded-full',
          liberado ? 'bg-success/15 text-success' : 'bg-primary/15 text-primary',
        )}
        title={`Parceiro: ${item.parceiro}`}
      >
        <Award className="size-6" aria-hidden />
      </span>

      <div className="min-w-0 flex-1">
        <p className="truncate font-display text-lg font-bold text-foreground">{item.nome}</p>
        <p className="text-sm text-muted-foreground">
          {item.parceiro}
          {item.carga_horaria ? ` · ${item.carga_horaria} horas` : ''}
        </p>
        {!liberado && (
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
              {item.concluidos}/{item.total_modulos} módulos
            </span>
          </div>
        )}
      </div>

      {liberado && item.certificado_id ? (
        <Button
          variant="secondary"
          disabled={baixar.isPending}
          onClick={() => baixar.mutate(item.certificado_id as number)}
        >
          <Download aria-hidden />
          Baixar PDF
        </Button>
      ) : (
        <Link
          to={`/trilhas/${item.slug}`}
          className="flex size-11 shrink-0 items-center justify-center rounded-full bg-muted text-locked"
          aria-label={`Certificado bloqueado: continuar a trilha ${item.nome}`}
        >
          <Lock className="size-5" />
        </Link>
      )}
    </motion.li>
  )
}

/**
 * Certificados das trilhas de parceiros (tela 20, #32): o liberado, para baixar,
 * e o que falta para cada um, por período. Só aparecem as trilhas de parceiros.
 */
export function CertificadosPage() {
  const usuario = useAuthStore((estado) => estado.usuario)
  const navigate = useNavigate()
  const certificados = useCertificados()
  const [escolhido, setEscolhido] = useState<number | null>(null)

  if (certificados.isPending) return <Carregando rotulo="Carregando certificados…" />
  if (certificados.isError) {
    return (
      <ErroAoCarregar
        erro={certificados.error}
        aoTentarDeNovo={() => void certificados.refetch()}
      />
    )
  }

  const grupos = certificados.data
  const chaves = grupos.map((g) => chaveDoPeriodo(g.periodo))
  const periodo =
    escolhido ??
    (usuario?.periodo && chaves.includes(usuario.periodo) ? usuario.periodo : (chaves[0] ?? 0))
  const doPeriodo = grupos.find((g) => chaveDoPeriodo(g.periodo) === periodo)?.itens ?? []
  const todos = grupos.flatMap((g) => g.itens)
  const conquistados = todos.filter((item) => item.estado === 'liberado').length

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
              <span
                className={cn(
                  'absolute -bottom-2 -right-4 flex size-14 items-center justify-center rounded-full border-4 border-card shadow',
                  conquistados ? 'bg-success text-success-foreground' : 'bg-muted text-locked',
                )}
                aria-hidden
              >
                <Award className="size-7" />
              </span>
            </div>

            <div>
              <p className="font-display text-5xl font-extrabold text-foreground">
                {conquistados}
                <span className="text-2xl text-muted-foreground"> de {todos.length}</span>
              </p>
              <p className="text-sm font-semibold text-muted-foreground">
                certificados conquistados
              </p>
            </div>

            {conquistados === 0 && (
              <div>
                <h2 className="font-display text-xl font-bold text-foreground">
                  Você ainda não tem certificados
                </h2>
                <p className="mx-auto max-w-xs text-muted-foreground">
                  Conclua todos os módulos de uma trilha para liberar o certificado do parceiro.
                </p>
              </div>
            )}

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

        <motion.section
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="flex flex-col rounded-lg border border-border bg-card p-6 shadow-sm xl:col-span-2"
        >
          <h2 className="font-display text-xl font-bold text-foreground">Veja seus certificados</h2>
          {grupos.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Ainda não há trilhas de parceiros no catálogo.
            </p>
          ) : (
            <>
              <p className="mb-4 text-sm text-muted-foreground">
                Cada trilha concluída libera um certificado. Escolha o período:
              </p>
              <div className="mb-5 flex flex-wrap gap-2" role="tablist" aria-label="Período">
                {chaves.map((chave) => {
                  const ativo = chave === periodo
                  const cores = coresPeriodo[chave]
                  return (
                    <button
                      key={chave}
                      type="button"
                      role="tab"
                      aria-selected={ativo}
                      onClick={() => setEscolhido(chave)}
                      className={cn(
                        'flex items-center gap-2 rounded-full border-2 py-1.5 pl-3 pr-4 text-sm font-bold transition-colors',
                        cores?.borda ?? 'border-border',
                        ativo
                          ? cn(cores?.cheio ?? 'bg-primary', 'text-periodo-foreground shadow-md')
                          : 'bg-card text-foreground hover:shadow-sm',
                      )}
                    >
                      {nomeDoPeriodo(chave)}
                    </button>
                  )
                })}
              </div>
              <div
                className={cn(
                  'flex-1 rounded-lg border-2 p-4',
                  coresPeriodo[periodo]?.borda ?? 'border-border',
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
                    {doPeriodo.map((item, i) => (
                      <ItemCertificado key={item.trilha_id} item={item} indice={i} />
                    ))}
                  </motion.ol>
                </AnimatePresence>
              </div>
            </>
          )}
        </motion.section>
      </div>
    </div>
  )
}
