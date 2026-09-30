import { useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  ChevronRight,
  Layers,
  MessagesSquare,
  Pencil,
  Search,
  SquarePen,
  Trash2,
  X,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { tempoRelativo } from '@/lib/tempo'
import { cn } from '@/lib/utils'
import type { Conversa, GrupoConversas } from '@/types/chat'

type ModoPainel = 'conversas' | 'agrupar'

function normalizar(texto: string) {
  return texto
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase()
}

function ItemConversa({
  conversa,
  ativa,
  onSelecionar,
  onExcluir,
}: {
  conversa: Conversa
  ativa: boolean
  onSelecionar: () => void
  onExcluir: () => void
}) {
  return (
    <motion.li
      layout
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -8 }}
      className="group relative"
    >
      <button
        type="button"
        onClick={onSelecionar}
        aria-current={ativa || undefined}
        className={cn(
          'flex w-full flex-col rounded-md px-3 py-2 pr-9 text-left transition-colors',
          ativa ? 'bg-primary/15' : 'hover:bg-muted',
        )}
      >
        <span
          className={cn(
            'truncate text-sm font-semibold',
            ativa ? 'text-primary' : 'text-foreground',
          )}
        >
          {conversa.titulo}
        </span>
        <span className="text-xs text-muted-foreground">
          {tempoRelativo(conversa.atualizadaEm)}
        </span>
      </button>
      <button
        type="button"
        onClick={onExcluir}
        aria-label={`Excluir conversa "${conversa.titulo}"`}
        className="absolute right-2 top-1/2 flex size-7 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive focus-visible:opacity-100 group-hover:opacity-100"
      >
        <Trash2 className="size-4" />
      </button>
    </motion.li>
  )
}

export function PainelConversas({
  conversas,
  grupos,
  ativaId,
  onSelecionar,
  onNova,
  onExcluir,
  onCriarGrupo,
  onDesfazerGrupo,
}: {
  conversas: Conversa[]
  grupos: GrupoConversas[]
  ativaId: string | null
  onSelecionar: (id: string) => void
  onNova: () => void
  onExcluir: (id: string) => void
  onCriarGrupo: (nome: string, conversaIds: string[]) => void
  onDesfazerGrupo: (grupoId: string) => void
}) {
  const [modo, setModo] = useState<ModoPainel>('conversas')
  const [busca, setBusca] = useState('')
  const [nomeGrupo, setNomeGrupo] = useState('')
  const [selecionadas, setSelecionadas] = useState<string[]>([])
  const [gruposFechados, setGruposFechados] = useState<string[]>([])

  const ordenadas = useMemo(
    () => [...conversas].sort((a, b) => b.atualizadaEm - a.atualizadaEm),
    [conversas],
  )
  const termo = normalizar(busca.trim())
  const resultadosBusca = termo
    ? ordenadas.filter((c) => normalizar(c.titulo).includes(termo))
    : null
  const semGrupo = ordenadas.filter((c) => !c.grupoId || !grupos.some((g) => g.id === c.grupoId))

  function alternarSelecao(id: string) {
    setSelecionadas((atuais) =>
      atuais.includes(id) ? atuais.filter((s) => s !== id) : [...atuais, id],
    )
  }

  function sairDoAgrupar() {
    setModo('conversas')
    setNomeGrupo('')
    setSelecionadas([])
  }

  function criarGrupo() {
    onCriarGrupo(nomeGrupo.trim(), selecionadas)
    sairDoAgrupar()
  }

  function renderItem(conversa: Conversa) {
    return (
      <ItemConversa
        key={conversa.id}
        conversa={conversa}
        ativa={conversa.id === ativaId}
        onSelecionar={() => onSelecionar(conversa.id)}
        onExcluir={() => onExcluir(conversa.id)}
      />
    )
  }

  return (
    <aside className="flex w-80 shrink-0 flex-col overflow-hidden rounded-lg border border-border bg-card shadow-sm">
      <div className="flex flex-col gap-3 border-b border-border p-4">
        <Button full onClick={onNova}>
          <SquarePen />
          Novo bate-papo
        </Button>
        <div className="grid grid-cols-2 gap-1 rounded-full bg-muted p-1" role="tablist">
          {(
            [
              { valor: 'conversas', rotulo: 'Conversas', icone: MessagesSquare },
              { valor: 'agrupar', rotulo: 'Agrupar', icone: Layers },
            ] as const
          ).map((aba) => (
            <button
              key={aba.valor}
              type="button"
              role="tab"
              aria-selected={modo === aba.valor}
              onClick={() => (aba.valor === 'conversas' ? sairDoAgrupar() : setModo('agrupar'))}
              className={cn(
                'relative flex items-center justify-center gap-1.5 rounded-full py-1.5 text-sm font-bold transition-colors',
                modo === aba.valor
                  ? 'text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {modo === aba.valor && (
                <motion.span
                  layoutId="aba-painel-chat"
                  className="absolute inset-0 rounded-full bg-primary shadow-sm"
                  transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                />
              )}
              <aba.icone className="relative size-4" />
              <span className="relative">{aba.rotulo}</span>
            </button>
          ))}
        </div>
      </div>

      <AnimatePresence mode="wait" initial={false}>
        {modo === 'conversas' ? (
          <motion.div
            key="conversas"
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -12 }}
            transition={{ duration: 0.2 }}
            className="flex min-h-0 flex-1 flex-col"
          >
            <div className="relative px-4 pt-4">
              <Search
                className="pointer-events-none absolute left-7 top-1/2 mt-2 size-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden
              />
              <Input
                type="search"
                value={busca}
                onChange={(event) => setBusca(event.target.value)}
                placeholder="Pesquisar chats..."
                aria-label="Pesquisar chats"
                className="h-10 bg-background pl-9 text-sm"
              />
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto px-2 py-3">
              {resultadosBusca ? (
                resultadosBusca.length > 0 ? (
                  <ul className="flex flex-col gap-0.5">
                    <AnimatePresence initial={false}>
                      {resultadosBusca.map(renderItem)}
                    </AnimatePresence>
                  </ul>
                ) : (
                  <p className="px-3 py-6 text-center text-sm text-muted-foreground">
                    Nenhuma conversa encontrada.
                  </p>
                )
              ) : (
                <>
                  {grupos.map((grupo) => {
                    const doGrupo = ordenadas.filter((c) => c.grupoId === grupo.id)
                    const aberto = !gruposFechados.includes(grupo.id)
                    return (
                      <div key={grupo.id} className="mb-2">
                        <div className="group flex items-center rounded-md hover:bg-muted">
                          <button
                            type="button"
                            onClick={() =>
                              setGruposFechados((atuais) =>
                                aberto
                                  ? [...atuais, grupo.id]
                                  : atuais.filter((g) => g !== grupo.id),
                              )
                            }
                            aria-expanded={aberto}
                            className="flex flex-1 items-center gap-2 px-2 py-2 text-left"
                          >
                            <motion.span animate={{ rotate: aberto ? 90 : 0 }} className="flex">
                              <ChevronRight className="size-4 text-muted-foreground" />
                            </motion.span>
                            <Layers className="size-4 text-primary" aria-hidden />
                            <span className="flex-1 truncate text-sm font-bold text-foreground">
                              {grupo.nome}
                            </span>
                            <span className="rounded-full bg-secondary px-2 text-xs font-bold text-muted-foreground">
                              {doGrupo.length}
                            </span>
                          </button>
                          <button
                            type="button"
                            onClick={() => onDesfazerGrupo(grupo.id)}
                            aria-label={`Desfazer grupo "${grupo.nome}"`}
                            title="Desfazer grupo"
                            className="mr-1 flex size-7 items-center justify-center rounded-md text-muted-foreground opacity-0 transition-opacity hover:text-destructive focus-visible:opacity-100 group-hover:opacity-100"
                          >
                            <X className="size-4" />
                          </button>
                        </div>
                        <AnimatePresence initial={false}>
                          {aberto && (
                            <motion.ul
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: 'auto', opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              className="ml-4 flex flex-col gap-0.5 overflow-hidden border-l-2 border-border pl-2"
                            >
                              <AnimatePresence initial={false}>
                                {doGrupo.map(renderItem)}
                              </AnimatePresence>
                            </motion.ul>
                          )}
                        </AnimatePresence>
                      </div>
                    )
                  })}

                  <p className="px-3 pb-1 pt-2 text-xs font-bold uppercase tracking-wide text-muted-foreground">
                    Recentes
                  </p>
                  {semGrupo.length > 0 ? (
                    <ul className="flex flex-col gap-0.5">
                      <AnimatePresence initial={false}>{semGrupo.map(renderItem)}</AnimatePresence>
                    </ul>
                  ) : (
                    <p className="px-3 py-2 text-sm text-muted-foreground">
                      Nenhuma conversa ainda.
                    </p>
                  )}
                </>
              )}
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="agrupar"
            initial={{ opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 12 }}
            transition={{ duration: 0.2 }}
            className="flex min-h-0 flex-1 flex-col"
          >
            <div className="relative px-4 pt-4">
              <Pencil
                className="pointer-events-none absolute left-7 top-1/2 mt-2 size-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden
              />
              <Input
                value={nomeGrupo}
                onChange={(event) => setNomeGrupo(event.target.value)}
                placeholder="Qual o nome do grupo..."
                aria-label="Nome do grupo"
                autoFocus
                className="h-10 bg-background pl-9 pr-12 text-sm"
              />
              <span
                className="absolute right-7 top-1/2 mt-2 -translate-y-1/2 text-sm font-bold text-primary"
                aria-label={`${selecionadas.length} selecionadas`}
              >
                {selecionadas.length}
              </span>
            </div>

            <p className="px-5 pt-3 text-xs text-muted-foreground">
              Selecione as conversas que farão parte do grupo.
            </p>

            <ul className="min-h-0 flex-1 overflow-y-auto px-2 py-2">
              {ordenadas.map((conversa) => {
                const marcada = selecionadas.includes(conversa.id)
                const grupoAtual = grupos.find((g) => g.id === conversa.grupoId)
                return (
                  <li key={conversa.id}>
                    <label
                      className={cn(
                        'flex cursor-pointer items-center gap-3 rounded-md px-3 py-2 transition-colors',
                        marcada ? 'bg-primary/10' : 'hover:bg-muted',
                      )}
                    >
                      <span className="flex min-w-0 flex-1 flex-col">
                        <span className="truncate text-sm font-semibold text-foreground">
                          {conversa.titulo}
                        </span>
                        {grupoAtual && (
                          <span className="truncate text-xs text-muted-foreground">
                            Em “{grupoAtual.nome}”
                          </span>
                        )}
                      </span>
                      <Checkbox
                        checked={marcada}
                        onCheckedChange={() => alternarSelecao(conversa.id)}
                      />
                    </label>
                  </li>
                )
              })}
            </ul>

            <div className="flex gap-2 border-t border-border p-4">
              <Button variant="ghost" className="flex-1" onClick={sairDoAgrupar}>
                Cancelar
              </Button>
              <Button
                className="flex-1"
                disabled={!nomeGrupo.trim() || selecionadas.length === 0}
                onClick={criarGrupo}
              >
                Criar grupo
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </aside>
  )
}
