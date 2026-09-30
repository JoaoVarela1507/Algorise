import { useId, useMemo, useState } from 'react'
import { AnimatePresence, motion, type Variants } from 'framer-motion'
import { Check, ChevronLeft, ChevronRight, Search, SlidersHorizontal, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { TrilhaCard } from '@/components/trilhas/TrilhaCard'
import { PERIODOS, coresPeriodo } from '@/components/trilhas/periodos'
import { useAuth } from '@/contexts/AuthContext'
import { cn } from '@/lib/utils'
import { INSTITUICAO_MOCK, trilhasMock } from '@/mocks/trilhas'
import mascotePolvo from '@/assets/images/mascote-polvo.png'

// 3 colunas × 3 linhas: a página cabe numa tela de desktop sem rolar.
const POR_PAGINA = 9

const grade: Variants = {
  oculto: {},
  visivel: { transition: { staggerChildren: 0.05 } },
}

const item: Variants = {
  oculto: { opacity: 0, y: 16 },
  visivel: { opacity: 1, y: 0, transition: { duration: 0.3, ease: 'easeOut' } },
}

function normalizar(texto: string) {
  return texto
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase()
}

const doisDigitos = (n: number) => String(n).padStart(2, '0')

export function TrilhasPage() {
  const { usuario } = useAuth()
  const [busca, setBusca] = useState('')
  const [periodos, setPeriodos] = useState<number[]>([])
  const [filtroAberto, setFiltroAberto] = useState(false)
  const [pagina, setPagina] = useState(0)
  const filtroId = useId()

  const filtradas = useMemo(() => {
    const termo = normalizar(busca.trim())
    return trilhasMock.filter(
      (trilha) =>
        // Busca só pelo nome da cadeira, casando com o começo dele ("re" → Redes…).
        (!termo || normalizar(trilha.nome).startsWith(termo)) &&
        (periodos.length === 0 || periodos.includes(trilha.periodo)),
    )
  }, [busca, periodos])

  const totalPaginas = Math.max(1, Math.ceil(filtradas.length / POR_PAGINA))
  const paginaAtual = Math.min(pagina, totalPaginas - 1)
  const inicio = paginaAtual * POR_PAGINA
  const visiveis = filtradas.slice(inicio, inicio + POR_PAGINA)

  function alternarPeriodo(periodo: number) {
    setPeriodos((atuais) =>
      atuais.includes(periodo) ? atuais.filter((p) => p !== periodo) : [...atuais, periodo],
    )
    setPagina(0)
  }

  function limparFiltros() {
    setBusca('')
    setPeriodos([])
    setPagina(0)
  }

  return (
    <>
      <div className="flex min-h-full flex-col gap-6">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="font-display text-3xl font-bold text-foreground">Trilhas</h1>
            <p className="text-muted-foreground">
              Ementa da{' '}
              <strong className="text-foreground">
                {usuario?.instituicao || INSTITUICAO_MOCK}
              </strong>
            </p>
          </div>

          <div className="flex w-full gap-3 sm:w-auto">
            <div className="relative flex-1 sm:w-80">
              <Search
                className="pointer-events-none absolute left-4 top-1/2 size-5 -translate-y-1/2 text-muted-foreground"
                aria-hidden
              />
              <Input
                type="search"
                placeholder="Buscar trilhas..."
                aria-label="Buscar trilhas"
                value={busca}
                onChange={(event) => {
                  setBusca(event.target.value)
                  setPagina(0)
                }}
                className="pl-11 shadow-sm"
              />
            </div>

            <Button
              variant={filtroAberto ? 'default' : 'secondary'}
              size="icon"
              onClick={() => setFiltroAberto((aberto) => !aberto)}
              aria-expanded={filtroAberto}
              aria-controls={filtroId}
              aria-label="Filtrar por período"
              className="relative shrink-0 shadow-sm"
            >
              <SlidersHorizontal />
              {periodos.length > 0 && (
                <motion.span
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="absolute -right-1 -top-1 flex size-5 items-center justify-center rounded-full bg-streak text-xs font-bold text-primary-foreground"
                >
                  {periodos.length}
                </motion.span>
              )}
            </Button>
          </div>
        </header>

        <AnimatePresence initial={false}>
          {filtroAberto && (
            <motion.div
              id={filtroId}
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25, ease: 'easeInOut' }}
              className="-mt-2 overflow-hidden"
            >
              <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-card p-4 shadow-sm">
                <span className="mr-2 text-sm font-bold text-muted-foreground">Período:</span>
                {PERIODOS.map((periodo, i) => {
                  const ativo = periodos.includes(periodo)
                  return (
                    <motion.button
                      key={periodo}
                      type="button"
                      initial={{ opacity: 0, y: -6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.03 }}
                      whileTap={{ scale: 0.92 }}
                      onClick={() => alternarPeriodo(periodo)}
                      aria-pressed={ativo}
                      className={cn(
                        'flex items-center gap-2 rounded-full border-2 py-1.5 pl-3 pr-4 text-sm font-bold transition-colors',
                        coresPeriodo[periodo].borda,
                        ativo
                          ? cn(coresPeriodo[periodo].cheio, 'text-periodo-foreground shadow-md')
                          : 'bg-card text-foreground hover:shadow-sm',
                      )}
                    >
                      {/* Desmarcado: bolinha na cor do período. Marcado: vira um check. */}
                      <span
                        className={cn(
                          'flex size-5 items-center justify-center rounded-full transition-colors',
                          ativo ? 'bg-card/80' : coresPeriodo[periodo].cheio,
                        )}
                        aria-hidden
                      >
                        <AnimatePresence initial={false}>
                          {ativo && (
                            <motion.span
                              initial={{ scale: 0, rotate: -90 }}
                              animate={{ scale: 1, rotate: 0 }}
                              exit={{ scale: 0 }}
                              transition={{ type: 'spring', stiffness: 500, damping: 20 }}
                            >
                              <Check className="size-3.5 text-foreground" strokeWidth={3.5} />
                            </motion.span>
                          )}
                        </AnimatePresence>
                      </span>
                      {periodo}º Período
                    </motion.button>
                  )
                })}
                {periodos.length > 0 && (
                  <button
                    type="button"
                    onClick={() => {
                      setPeriodos([])
                      setPagina(0)
                    }}
                    className="ml-auto flex items-center gap-1 text-sm font-semibold text-muted-foreground hover:text-foreground"
                  >
                    <X className="size-4" />
                    Limpar
                  </button>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {visiveis.length > 0 ? (
          <motion.ul
            key={paginaAtual}
            variants={grade}
            initial="oculto"
            animate="visivel"
            className="grid auto-rows-fr gap-5 md:grid-cols-2 xl:grid-cols-3"
          >
            <AnimatePresence mode="popLayout">
              {visiveis.map((trilha) => (
                <motion.li
                  key={trilha.id}
                  layout
                  variants={item}
                  exit={{ opacity: 0, scale: 0.95 }}
                >
                  <TrilhaCard trilha={trilha} />
                </motion.li>
              ))}
            </AnimatePresence>
          </motion.ul>
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-1 flex-col items-center justify-center gap-3 text-center"
          >
            <motion.img
              src={mascotePolvo}
              alt=""
              className="h-28"
              animate={{ rotate: [0, -6, 6, 0] }}
              transition={{ duration: 3, repeat: Infinity }}
            />
            <p className="font-display text-xl font-bold text-foreground">
              Nenhuma trilha encontrada
            </p>
            <p className="text-muted-foreground">Tente outro termo ou limpe os filtros.</p>
            <Button variant="outline" onClick={limparFiltros}>
              Limpar filtros
            </Button>
          </motion.div>
        )}

        {filtradas.length > 0 && (
          <nav
            aria-label="Paginação"
            className="mt-auto flex items-center justify-center gap-4 pt-2"
          >
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setPagina(paginaAtual - 1)}
              disabled={paginaAtual === 0}
              aria-label="Página anterior"
            >
              <ChevronLeft />
            </Button>
            <span className="font-display text-lg font-bold text-foreground" aria-live="polite">
              {doisDigitos(inicio + 1)}–{doisDigitos(inicio + visiveis.length)}{' '}
              <span className="text-muted-foreground">de {doisDigitos(filtradas.length)}</span>
            </span>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setPagina(paginaAtual + 1)}
              disabled={paginaAtual >= totalPaginas - 1}
              aria-label="Próxima página"
            >
              <ChevronRight />
            </Button>
          </nav>
        )}
      </div>
    </>
  )
}
