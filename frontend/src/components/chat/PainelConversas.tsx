import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Check,
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
import { toast } from '@/components/ui/toaster'
import { useDebounce } from '@/hooks/useDebounce'
import {
  useApagarConversa,
  useApagarGrupo,
  useConversas,
  useCriarGrupo,
  useEditarGrupo,
  useGrupos,
  useRenomearConversa,
} from '@/hooks/useChat'
import { tempoRelativo } from '@/lib/tempo'
import { cn } from '@/lib/utils'
import type { ConversaResumo, GrupoDeConversas } from '@/services/chat'

type ModoPainel = 'conversas' | 'agrupar'

// Em tela de toque não existe hover: os botões de ação ficam sempre visíveis.
const ACAO_NO_HOVER =
  'opacity-0 transition-opacity focus-visible:opacity-100 group-hover:opacity-100 [@media(hover:none)]:opacity-100'

function erroDaAcao(erro: unknown, padrao: string) {
  return erro instanceof Error && erro.message ? erro.message : padrao
}

function ItemConversa({
  conversa,
  ativa,
  onSelecionar,
  onExcluida,
}: {
  conversa: ConversaResumo
  ativa: boolean
  onSelecionar: () => void
  onExcluida: () => void
}) {
  const renomear = useRenomearConversa()
  const apagar = useApagarConversa()
  const [editando, setEditando] = useState(false)
  const [titulo, setTitulo] = useState(conversa.titulo)
  const [confirmando, setConfirmando] = useState(false)

  function salvar() {
    const novo = titulo.trim()
    if (!novo || novo === conversa.titulo) {
      setEditando(false)
      return
    }
    renomear.mutate(
      { id: conversa.id, titulo: novo },
      {
        onSuccess: () => setEditando(false),
        onError: (erro) => toast.error(erroDaAcao(erro, 'Não foi possível renomear.')),
      },
    )
  }

  function excluir() {
    apagar.mutate(conversa.id, {
      onSuccess: onExcluida,
      onError: (erro) => {
        setConfirmando(false)
        toast.error(erroDaAcao(erro, 'Não foi possível apagar a conversa.'))
      },
    })
  }

  return (
    <motion.li
      layout
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -8 }}
      className="group relative"
    >
      {editando ? (
        <form
          className="flex items-center gap-1 px-1 py-1"
          onSubmit={(event) => {
            event.preventDefault()
            salvar()
          }}
        >
          <Input
            value={titulo}
            onChange={(event) => setTitulo(event.target.value)}
            maxLength={120}
            autoFocus
            aria-label="Novo título da conversa"
            className="h-9 min-w-0 flex-1 text-sm"
          />
          <button
            type="submit"
            disabled={renomear.isPending}
            aria-label="Salvar título"
            className="flex size-8 shrink-0 items-center justify-center rounded-md text-primary hover:bg-muted"
          >
            <Check className="size-4" />
          </button>
          <button
            type="button"
            onClick={() => {
              setTitulo(conversa.titulo)
              setEditando(false)
            }}
            aria-label="Cancelar"
            className="flex size-8 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-muted"
          >
            <X className="size-4" />
          </button>
        </form>
      ) : confirmando ? (
        <div className="flex items-center gap-1 rounded-md bg-destructive/10 px-3 py-2">
          <span className="min-w-0 flex-1 truncate text-sm font-semibold text-destructive">
            Apagar esta conversa?
          </span>
          <Button
            size="sm"
            variant="destructive"
            disabled={apagar.isPending}
            onClick={excluir}
            aria-label={`Confirmar exclusão de "${conversa.titulo}"`}
          >
            Apagar
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setConfirmando(false)}>
            Não
          </Button>
        </div>
      ) : (
        <>
          <button
            type="button"
            onClick={onSelecionar}
            aria-current={ativa || undefined}
            className={cn(
              'flex w-full flex-col rounded-md px-3 py-2 pr-16 text-left transition-colors',
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
              {tempoRelativo(Date.parse(conversa.atualizado_em))}
            </span>
          </button>
          <div className="absolute right-1 top-1/2 flex -translate-y-1/2 items-center">
            <button
              type="button"
              onClick={() => {
                setTitulo(conversa.titulo)
                setEditando(true)
              }}
              aria-label={`Renomear conversa "${conversa.titulo}"`}
              className={cn(
                'flex size-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground',
                ACAO_NO_HOVER,
              )}
            >
              <Pencil className="size-4" />
            </button>
            <button
              type="button"
              onClick={() => setConfirmando(true)}
              aria-label={`Excluir conversa "${conversa.titulo}"`}
              className={cn(
                'flex size-7 items-center justify-center rounded-md text-muted-foreground hover:bg-destructive/10 hover:text-destructive',
                ACAO_NO_HOVER,
              )}
            >
              <Trash2 className="size-4" />
            </button>
          </div>
        </>
      )}
    </motion.li>
  )
}

export function PainelConversas({
  ativaId,
  onSelecionar,
  onNova,
  onExcluida,
}: {
  ativaId: number | null
  onSelecionar: (conversa: ConversaResumo) => void
  onNova: () => void
  /** Uma conversa foi apagada: quem a mostra precisa sair dela. */
  onExcluida: (id: number) => void
}) {
  const [modo, setModo] = useState<ModoPainel>('conversas')
  const [busca, setBusca] = useState('')
  const [nomeGrupo, setNomeGrupo] = useState('')
  const [selecionadas, setSelecionadas] = useState<number[]>([])
  // Grupo que está sendo editado na aba "Agrupar"; `null` cria um novo.
  const [grupoEditando, setGrupoEditando] = useState<GrupoDeConversas | null>(null)
  const [gruposFechados, setGruposFechados] = useState<number[]>([])

  // A busca roda no servidor (título e conteúdo das mensagens): espera o aluno
  // parar de digitar para não disparar uma requisição por letra.
  const termo = useDebounce(busca.trim())
  const conversasQuery = useConversas(termo)
  const gruposQuery = useGrupos()
  const criarGrupo = useCriarGrupo()
  const editarGrupo = useEditarGrupo()
  const apagarGrupo = useApagarGrupo()

  const conversas = conversasQuery.data?.pages.flatMap((pagina) => pagina.itens) ?? []
  const grupos = gruposQuery.data ?? []
  const buscando = termo !== ''
  const semGrupo = conversas.filter((c) => c.grupo_id === null)
  // Na aba "Agrupar" entram também as conversas do grupo que ainda não vieram
  // na lista paginada, para dar para desmarcá-las.
  const candidatas = [
    ...conversas,
    ...(grupoEditando?.conversas.filter((g) => !conversas.some((c) => c.id === g.id)) ?? []),
  ]

  function alternarSelecao(id: number) {
    setSelecionadas((atuais) =>
      atuais.includes(id) ? atuais.filter((s) => s !== id) : [...atuais, id],
    )
  }

  function sairDoAgrupar() {
    setModo('conversas')
    setNomeGrupo('')
    setSelecionadas([])
    setGrupoEditando(null)
  }

  function editarMembros(grupo: GrupoDeConversas) {
    setGrupoEditando(grupo)
    setNomeGrupo(grupo.nome)
    setSelecionadas(grupo.conversas.map((c) => c.id))
    setModo('agrupar')
  }

  function salvarGrupo() {
    const nome = nomeGrupo.trim()
    const aoErrar = (erro: unknown) =>
      toast.error(erroDaAcao(erro, 'Não foi possível salvar o grupo.'))
    if (grupoEditando) {
      editarGrupo.mutate(
        { id: grupoEditando.id, nome, conversaIds: selecionadas },
        { onSuccess: sairDoAgrupar, onError: aoErrar },
      )
    } else {
      criarGrupo.mutate(
        { nome, conversaIds: selecionadas },
        { onSuccess: sairDoAgrupar, onError: aoErrar },
      )
    }
  }

  function renderItem(conversa: ConversaResumo) {
    return (
      <ItemConversa
        key={conversa.id}
        conversa={conversa}
        ativa={conversa.id === ativaId}
        onSelecionar={() => onSelecionar(conversa)}
        onExcluida={() => onExcluida(conversa.id)}
      />
    )
  }

  const verMais = conversasQuery.hasNextPage && (
    <Button
      variant="ghost"
      size="sm"
      full
      disabled={conversasQuery.isFetchingNextPage}
      onClick={() => void conversasQuery.fetchNextPage()}
    >
      Ver mais
    </Button>
  )

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
              {conversasQuery.isError || gruposQuery.isError ? (
                <p role="alert" className="px-3 py-6 text-center text-sm text-muted-foreground">
                  Não foi possível carregar suas conversas.{' '}
                  <button
                    type="button"
                    className="font-semibold text-primary underline"
                    onClick={() => {
                      void conversasQuery.refetch()
                      void gruposQuery.refetch()
                    }}
                  >
                    Tentar de novo
                  </button>
                </p>
              ) : conversasQuery.isPending ? (
                <p className="px-3 py-6 text-center text-sm text-muted-foreground">Carregando…</p>
              ) : buscando ? (
                conversas.length > 0 ? (
                  <>
                    <ul className="flex flex-col gap-0.5">
                      <AnimatePresence initial={false}>{conversas.map(renderItem)}</AnimatePresence>
                    </ul>
                    {verMais}
                  </>
                ) : (
                  <p className="px-3 py-6 text-center text-sm text-muted-foreground">
                    Nenhuma conversa encontrada.
                  </p>
                )
              ) : (
                <>
                  {grupos.map((grupo) => {
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
                            className="flex min-w-0 flex-1 items-center gap-2 px-2 py-2 text-left"
                          >
                            <motion.span animate={{ rotate: aberto ? 90 : 0 }} className="flex">
                              <ChevronRight className="size-4 text-muted-foreground" />
                            </motion.span>
                            <Layers className="size-4 shrink-0 text-primary" aria-hidden />
                            <span className="flex-1 truncate text-sm font-bold text-foreground">
                              {grupo.nome}
                            </span>
                            <span className="rounded-full bg-secondary px-2 text-xs font-bold text-muted-foreground">
                              {grupo.conversas.length}
                            </span>
                          </button>
                          <button
                            type="button"
                            onClick={() => editarMembros(grupo)}
                            aria-label={`Editar grupo "${grupo.nome}"`}
                            title="Renomear ou trocar as conversas do grupo"
                            className={cn(
                              'flex size-7 items-center justify-center rounded-md text-muted-foreground hover:text-foreground',
                              ACAO_NO_HOVER,
                            )}
                          >
                            <Pencil className="size-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() =>
                              apagarGrupo.mutate(grupo.id, {
                                onError: (erro) =>
                                  toast.error(
                                    erroDaAcao(erro, 'Não foi possível desfazer o grupo.'),
                                  ),
                              })
                            }
                            aria-label={`Desfazer grupo "${grupo.nome}"`}
                            title="Desfazer grupo (as conversas ficam)"
                            className={cn(
                              'mr-1 flex size-7 items-center justify-center rounded-md text-muted-foreground hover:text-destructive',
                              ACAO_NO_HOVER,
                            )}
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
                                {grupo.conversas.map(renderItem)}
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
                  {verMais}
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
                maxLength={80}
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
              {grupoEditando
                ? 'Marque as conversas que ficam no grupo; as desmarcadas saem dele.'
                : 'Selecione as conversas que farão parte do grupo.'}
            </p>

            <ul className="min-h-0 flex-1 overflow-y-auto px-2 py-2">
              {candidatas.map((conversa) => {
                const marcada = selecionadas.includes(conversa.id)
                const grupoAtual = grupos.find((g) => g.id === conversa.grupo_id)
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
              {verMais && <li>{verMais}</li>}
            </ul>

            <div className="flex gap-2 border-t border-border p-4">
              <Button variant="ghost" className="flex-1" onClick={sairDoAgrupar}>
                Cancelar
              </Button>
              <Button
                className="flex-1"
                disabled={
                  !nomeGrupo.trim() ||
                  (!grupoEditando && selecionadas.length === 0) ||
                  criarGrupo.isPending ||
                  editarGrupo.isPending
                }
                onClick={salvarGrupo}
              >
                {grupoEditando ? 'Salvar grupo' : 'Criar grupo'}
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </aside>
  )
}
