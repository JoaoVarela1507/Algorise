import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { Layers, MessagesSquare, Square, SquarePen } from 'lucide-react'
import { Composer } from '@/components/chat/Composer'
import { mensagemDeErro, podeTentarDeNovo } from '@/components/chat/erros'
import {
  IndicadorDigitando,
  MensagemChat,
  type MensagemDoChat,
} from '@/components/chat/MensagemChat'
import { PainelConversas } from '@/components/chat/PainelConversas'
import { Button } from '@/components/ui/button'
import { atualizarDepoisDaResposta, useConversas, useGrupos, useMensagens } from '@/hooks/useChat'
import { saudacaoDoHorario } from '@/lib/tempo'
import { type AnexoDoChat, type ConversaResumo, type MensagemApi } from '@/services/chat'
import { perguntar } from '@/services/chatAoVivo'
import { useAuthStore } from '@/stores/useAuthStore'
import { tempoReal } from '@/stores/useTempoRealStore'
import type { ModoResposta } from '@/types/chat'
import mascotePolvo from '@/assets/images/mascote-polvo.png'

const sugestoes = [
  'Me explica recursão com um exemplo',
  'Qual a diferença entre TCP e UDP?',
  'Como funciona a minha ementa?',
]

const SEM_RESPOSTA = 'O tutor não chegou a responder. Tente de novo.'

/** Conversa aberta. O título vem junto porque a lista pode não ter a conversa (busca ativa). */
interface ConversaAberta {
  id: number
  titulo: string
}

/**
 * O que está na tela mas ainda não é (ou não está só) na API: a pergunta
 * enviada, antes de o servidor devolver o histórico, e o erro da resposta.
 */
interface Pendente {
  /** A conversa em que a mensagem entra; `null` é uma conversa que ainda vai nascer. */
  conversaId: number | null
  pergunta?: MensagemDoChat
  /** Quantas mensagens a API tinha ao enviar: com mais que isso, a pergunta já veio de lá. */
  base: number
  erro?: MensagemDoChat
}

function daApi(mensagem: MensagemApi): MensagemDoChat {
  // Resposta cortada sem texto nenhum (a IA caiu antes do primeiro pedaço) vira
  // erro, com "Tentar de novo", em vez de uma bolha vazia.
  const vazia = mensagem.papel === 'assistente' && mensagem.incompleta && !mensagem.conteudo
  return {
    id: String(mensagem.id),
    autor: mensagem.papel,
    conteudo: vazia ? SEM_RESPOSTA : mensagem.conteudo,
    criadaEm: Date.parse(mensagem.criado_em),
    anexos: mensagem.anexos,
    erro: vazia,
    // A faixa "Resposta interrompida" aparece na mensagem, não no texto.
    incompleta: mensagem.incompleta && !vazia,
  }
}

function mensagemLocal(dados: Omit<MensagemDoChat, 'id' | 'criadaEm'>): MensagemDoChat {
  return { id: crypto.randomUUID(), criadaEm: Date.now(), ...dados }
}

/**
 * Área rolável das mensagens. Fica grudada no fim enquanto a resposta
 * "digita", a menos que a pessoa tenha subido para reler algo; mandar uma
 * mensagem nova sempre volta para o fim.
 */
function ListaMensagens({
  mensagens,
  aguardando,
  parcial,
  aoTentarDeNovo,
}: {
  mensagens: MensagemDoChat[]
  aguardando: boolean
  /** A resposta chegando, pedaço a pedaço (#36). */
  parcial: string
  aoTentarDeNovo: () => void
}) {
  const rolagemRef = useRef<HTMLDivElement>(null)
  const conteudoRef = useRef<HTMLDivElement>(null)
  const grudadoNoFimRef = useRef(true)
  const ultima = mensagens[mensagens.length - 1]
  // "Tentar de novo" só na última resposta, e só se ela falhou ou veio cortada.
  const podeRepetir =
    !aguardando &&
    ultima?.autor === 'assistente' &&
    (ultima.erro || ultima.incompleta) &&
    !ultima.semRetentativa

  useEffect(() => {
    const rolagem = rolagemRef.current
    const conteudo = conteudoRef.current
    if (!rolagem || !conteudo) return
    rolagem.scrollTop = rolagem.scrollHeight
    const observador = new ResizeObserver(() => {
      if (grudadoNoFimRef.current) rolagem.scrollTop = rolagem.scrollHeight
    })
    observador.observe(conteudo)
    return () => observador.disconnect()
  }, [])

  useEffect(() => {
    if (ultima?.autor === 'usuario') grudadoNoFimRef.current = true
  }, [ultima])

  return (
    <div
      ref={rolagemRef}
      onScroll={(event) => {
        const alvo = event.currentTarget
        grudadoNoFimRef.current = alvo.scrollHeight - alvo.scrollTop - alvo.clientHeight < 48
      }}
      className="min-h-0 flex-1 overflow-y-auto"
    >
      <div ref={conteudoRef} className="mx-auto flex max-w-3xl flex-col gap-5 py-6">
        {mensagens.map((mensagem) => (
          <MensagemChat
            key={mensagem.id}
            mensagem={mensagem}
            aoTentarDeNovo={podeRepetir && mensagem === ultima ? aoTentarDeNovo : undefined}
          />
        ))}
        {aguardando && parcial && (
          <MensagemChat
            mensagem={{ id: 'parcial', autor: 'assistente', conteudo: parcial, criadaEm: 0 }}
          />
        )}
        <AnimatePresence>{aguardando && !parcial && <IndicadorDigitando />}</AnimatePresence>
      </div>
    </div>
  )
}

export function ChatPage() {
  const queryClient = useQueryClient()
  const usuario = useAuthStore((estado) => estado.usuario)
  const [ativa, setAtiva] = useState<ConversaAberta | null>(null)
  const [modo, setModo] = useState<ModoResposta>('medio')
  const [pendente, setPendente] = useState<Pendente | null>(null)
  // Em que conversa (`null`: uma nova) o tutor está respondendo agora.
  const [aguardando, setAguardando] = useState<{ conversaId: number | null } | null>(null)
  const [parcial, setParcial] = useState('')
  const [painelAberto, setPainelAberto] = useState(false)
  // Para a resposta em curso: pelo WebSocket ou cortando o SSE.
  const pararRef = useRef<(() => void) | null>(null)

  const conversasQuery = useConversas()
  const gruposQuery = useGrupos()
  const mensagensQuery = useMensagens(ativa?.id ?? null)

  const ativaId = ativa?.id ?? null
  const conversas = conversasQuery.data?.pages.flatMap((pagina) => pagina.itens) ?? []
  const grupos = gruposQuery.data ?? []
  const temHistorico = (conversasQuery.data?.pages[0]?.total ?? 0) > 0
  const tituloAtivo =
    conversas.find((c) => c.id === ativaId)?.titulo ??
    grupos.flatMap((g) => g.conversas).find((c) => c.id === ativaId)?.titulo ??
    ativa?.titulo ??
    ''
  const grupoAtivo = grupos.find((g) => g.conversas.some((c) => c.id === ativaId))
  const primeiroNome = usuario?.nome.split(' ')[0] ?? 'estudante'

  const doServidor = (mensagensQuery.data ?? []).map(daApi)
  const pendenteAqui = pendente !== null && pendente.conversaId === ativaId ? pendente : null
  const mensagens = [
    ...doServidor,
    // A pergunta só aparece daqui até a API devolver o histórico com ela.
    ...(pendenteAqui?.pergunta && doServidor.length <= pendenteAqui.base
      ? [pendenteAqui.pergunta]
      : []),
    ...(pendenteAqui?.erro ? [pendenteAqui.erro] : []),
  ]
  // Uma conversa nova ainda sem id também já é a tela de conversa.
  const emConversa = ativa !== null || pendente?.conversaId === null
  const ocupado = aguardando !== null
  const aguardandoAqui = aguardando !== null && aguardando.conversaId === ativaId

  /**
   * `reenvio`: repete a última pergunta sem duplicá-la na tela; o erro da
   * resposta anterior sai para o novo resultado ocupar o fim da conversa.
   */
  async function enviar(texto: string, anexos: AnexoDoChat[] = [], reenvio = false) {
    const conversaId = ativaId
    const pergunta = reenvio
      ? undefined
      : mensagemLocal({ autor: 'usuario', conteudo: texto, anexos })
    setPendente((atual) => ({
      conversaId,
      pergunta: reenvio ? atual?.pergunta : pergunta,
      base: reenvio ? (atual?.base ?? doServidor.length) : doServidor.length,
    }))
    setAguardando({ conversaId })
    setParcial('')

    // Depois de a resposta chegar a API tem a conversa inteira: o que estava só
    // na tela sai, e a tela passa a mostrar o histórico de lá.
    const recarregar = async (id: number) => {
      try {
        await atualizarDepoisDaResposta(queryClient, id)
      } catch {
        // Sem rede para recarregar: a pergunta local continua na tela.
      }
    }

    try {
      const aoVivo = perguntar(
        tempoReal,
        {
          conversaId: conversaId ?? undefined,
          conteudo: texto,
          modo,
          anexoIds: anexos.map((a) => a.id),
        },
        setParcial,
      )
      pararRef.current = aoVivo.parar
      const doTutor = await aoVivo.resposta
      await recarregar(doTutor.conversaId)
      // Conversa nova: abre a que o servidor criou, se a pessoa ainda estiver na tela de nova.
      setAtiva((atual) =>
        atual === null && conversaId === null
          ? { id: doTutor.conversaId, titulo: doTutor.titulo }
          : atual,
      )
      setPendente(
        doTutor.resposta
          ? null
          : {
              conversaId: doTutor.conversaId,
              base: 0,
              erro: mensagemLocal({ autor: 'assistente', conteudo: SEM_RESPOSTA, erro: true }),
            },
      )
    } catch (erro) {
      if (conversaId !== null) await recarregar(conversaId)
      setPendente((atual) => ({
        conversaId,
        pergunta: atual?.pergunta,
        base: atual?.base ?? doServidor.length,
        erro: mensagemLocal({
          autor: 'assistente',
          conteudo: mensagemDeErro(erro),
          erro: true,
          semRetentativa: !podeTentarDeNovo(erro),
        }),
      }))
    } finally {
      pararRef.current = null
      setParcial('')
      setAguardando(null)
    }
  }

  function tentarDeNovo() {
    const ultimaPergunta = mensagens.filter((m) => m.autor === 'usuario').pop()
    if (ultimaPergunta && !ocupado) void enviar(ultimaPergunta.conteudo, [], true)
  }

  function abrirConversa(conversa: ConversaResumo | null) {
    // Sai o erro da conversa anterior; a pergunta em curso fica, para a
    // resposta cair no lugar certo quando chegar.
    setPendente((atual) => (aguardando ? atual : null))
    setAtiva(conversa && { id: conversa.id, titulo: conversa.titulo })
  }

  function conversaApagada(id: number) {
    if (id !== ativaId) return
    setPendente(null)
    setAtiva(null)
  }

  const painel = (aoEscolher?: () => void) => (
    <PainelConversas
      ativaId={ativaId}
      onSelecionar={(conversa) => {
        abrirConversa(conversa)
        aoEscolher?.()
      }}
      onNova={() => {
        abrirConversa(null)
        aoEscolher?.()
      }}
      onExcluida={conversaApagada}
    />
  )

  // Abaixo do `lg` o painel não cabe ao lado: vira gaveta, aberta pelo botão
  // "Conversas". Sem ela, no celular não havia como voltar a uma conversa antiga.
  const botaoConversas = (
    <Button
      variant="secondary"
      size="sm"
      className="lg:hidden"
      onClick={() => setPainelAberto(true)}
      aria-label="Abrir conversas"
    >
      <MessagesSquare />
      Conversas
    </Button>
  )

  return (
    <>
      <AnimatePresence>
        {painelAberto && (
          <motion.div
            className="fixed inset-0 z-50 lg:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <button
              type="button"
              aria-label="Fechar conversas"
              className="absolute inset-0 bg-foreground/30"
              onClick={() => setPainelAberto(false)}
            />
            <motion.div
              role="dialog"
              aria-label="Conversas"
              className="absolute inset-y-0 left-0 flex w-[min(20rem,88vw)] bg-background p-3 shadow-xl [&>aside]:w-full"
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', stiffness: 380, damping: 36 }}
            >
              {painel(() => setPainelAberto(false))}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex h-full gap-6">
        <div className="hidden lg:flex">{painel()}</div>

        <section className="flex min-w-0 flex-1 flex-col">
          <AnimatePresence mode="wait" initial={false}>
            {emConversa ? (
              <motion.div
                key={ativaId ?? 'nova'}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
                className="flex min-h-0 flex-1 flex-col"
              >
                <header className="flex items-center gap-2 border-b border-border pb-4 sm:gap-3">
                  {botaoConversas}
                  <div className="min-w-0 flex-1">
                    <h1 className="truncate font-display text-xl font-bold text-foreground">
                      {ativa ? tituloAtivo : 'Nova conversa'}
                    </h1>
                    {grupoAtivo && (
                      <span className="flex items-center gap-1 text-xs font-semibold text-muted-foreground">
                        <Layers className="size-3.5" aria-hidden />
                        <span className="truncate">{grupoAtivo.nome}</span>
                      </span>
                    )}
                  </div>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => abrirConversa(null)}
                    aria-label="Novo bate-papo"
                  >
                    <SquarePen />
                    {/* No celular, só o ícone: o título da conversa precisa do espaço. */}
                    <span className="hidden sm:inline">Novo bate-papo</span>
                  </Button>
                </header>

                {mensagensQuery.isPending && ativa ? (
                  <p
                    role="status"
                    className="flex-1 py-10 text-center text-sm text-muted-foreground"
                  >
                    Carregando a conversa…
                  </p>
                ) : mensagensQuery.isError ? (
                  <p
                    role="alert"
                    className="flex-1 px-4 py-10 text-center text-sm text-muted-foreground"
                  >
                    Não foi possível carregar esta conversa.{' '}
                    <button
                      type="button"
                      className="font-semibold text-primary underline"
                      onClick={() => void mensagensQuery.refetch()}
                    >
                      Tentar de novo
                    </button>
                  </p>
                ) : (
                  <ListaMensagens
                    mensagens={mensagens}
                    aguardando={aguardandoAqui}
                    parcial={parcial}
                    aoTentarDeNovo={tentarDeNovo}
                  />
                )}

                {aguardandoAqui && (
                  <div className="flex justify-center pt-2">
                    <Button variant="secondary" size="sm" onClick={() => pararRef.current?.()}>
                      <Square />
                      Parar resposta
                    </Button>
                  </div>
                )}

                <div className="mx-auto w-full max-w-3xl pt-2">
                  <Composer
                    onEnviar={enviar}
                    ocupado={ocupado}
                    modo={modo}
                    onModoChange={setModo}
                    autoFocus
                  />
                  <p className="mt-2 text-center text-xs text-muted-foreground">
                    O Algorise pode cometer erros. Confira informações importantes.
                  </p>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="boas-vindas"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -12 }}
                transition={{ duration: 0.25 }}
                className="relative flex flex-1 flex-col items-center justify-center gap-6 px-4"
              >
                {temHistorico && <div className="absolute left-0 top-0">{botaoConversas}</div>}
                <motion.img
                  src={mascotePolvo}
                  alt=""
                  className="h-36 select-none"
                  draggable={false}
                  animate={{ y: [0, -10, 0], rotate: [0, -3, 3, 0] }}
                  transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
                />
                <div className="text-center">
                  <h1 className="font-display text-3xl text-foreground">
                    {saudacaoDoHorario()}, <strong>{primeiroNome}</strong>
                  </h1>
                  <p className="mt-1 text-muted-foreground">
                    Tire dúvidas de programação e das disciplinas da sua ementa.
                  </p>
                </div>

                <Composer
                  onEnviar={enviar}
                  ocupado={ocupado}
                  modo={modo}
                  onModoChange={setModo}
                  autoFocus
                  className="max-w-2xl"
                />

                <div className="flex max-w-2xl flex-wrap justify-center gap-2">
                  {sugestoes.map((sugestao, i) => (
                    <motion.button
                      key={sugestao}
                      type="button"
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.2 + i * 0.08 }}
                      whileHover={{ y: -2 }}
                      onClick={() => enviar(sugestao)}
                      disabled={ocupado}
                      className="rounded-full border border-border bg-card px-4 py-2 text-sm font-semibold text-foreground shadow-sm transition-colors hover:border-primary/50 hover:text-primary"
                    >
                      {sugestao}
                    </motion.button>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </section>
      </div>
    </>
  )
}
