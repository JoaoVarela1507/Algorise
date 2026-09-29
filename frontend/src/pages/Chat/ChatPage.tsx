import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Layers, SquarePen } from 'lucide-react'
import { Composer } from '@/components/chat/Composer'
import { IndicadorDigitando, MensagemChat } from '@/components/chat/MensagemChat'
import { PainelConversas } from '@/components/chat/PainelConversas'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/contexts/AuthContext'
import { saudacaoDoHorario } from '@/lib/tempo'
import { conversasIniciais, gruposIniciais } from '@/mocks/chat'
import { CHAVE_HISTORICO_CHAT, enviarMensagem } from '@/services/chat'
import type { Conversa, GrupoConversas, Mensagem, ModoResposta } from '@/types/chat'
import mascotePolvo from '@/assets/images/mascote-polvo.png'

const sugestoes = [
  'Me explica recursão com um exemplo',
  'Qual a diferença entre TCP e UDP?',
  'Como funciona a minha ementa?',
]

interface EstadoChat {
  conversas: Conversa[]
  grupos: GrupoConversas[]
}

// Enquanto não há backend, o histórico fica só neste navegador.
function carregarEstado(): EstadoChat {
  try {
    const salvo = localStorage.getItem(CHAVE_HISTORICO_CHAT)
    if (salvo) return JSON.parse(salvo) as EstadoChat
  } catch {
    // Armazenamento indisponível (aba anônima, bloqueio): segue com o exemplo.
  }
  return { conversas: conversasIniciais(), grupos: gruposIniciais }
}

function tituloDe(texto: string) {
  const linha = texto.split('\n')[0].trim()
  return linha.length > 40 ? `${linha.slice(0, 40).trimEnd()}…` : linha
}

function novaMensagem(dados: Omit<Mensagem, 'id' | 'criadaEm'>): Mensagem {
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
  digitandoMensagemId,
}: {
  mensagens: Mensagem[]
  aguardando: boolean
  digitandoMensagemId: string | null
}) {
  const rolagemRef = useRef<HTMLDivElement>(null)
  const conteudoRef = useRef<HTMLDivElement>(null)
  const grudadoNoFimRef = useRef(true)
  const ultima = mensagens[mensagens.length - 1]

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
            animarDigitacao={mensagem.id === digitandoMensagemId}
          />
        ))}
        <AnimatePresence>{aguardando && <IndicadorDigitando />}</AnimatePresence>
      </div>
    </div>
  )
}

export function ChatPage() {
  const { usuario } = useAuth()
  const [estado, setEstado] = useState(carregarEstado)
  const [ativaId, setAtivaId] = useState<string | null>(null)
  const [modo, setModo] = useState<ModoResposta>('medio')
  const [aguardandoId, setAguardandoId] = useState<string | null>(null)
  const [digitandoMensagemId, setDigitandoMensagemId] = useState<string | null>(null)

  useEffect(() => {
    try {
      localStorage.setItem(CHAVE_HISTORICO_CHAT, JSON.stringify(estado))
    } catch {
      // Sem armazenamento: o chat funciona, só não persiste.
    }
  }, [estado])

  const conversaAtiva = estado.conversas.find((c) => c.id === ativaId) ?? null
  const grupoAtivo = estado.grupos.find((g) => g.id === conversaAtiva?.grupoId)
  const primeiroNome = usuario?.nome.split(' ')[0] ?? 'estudante'

  function adicionarMensagem(conversaId: string, mensagem: Mensagem) {
    setEstado((atual) => ({
      ...atual,
      conversas: atual.conversas.map((c) =>
        c.id === conversaId
          ? { ...c, mensagens: [...c.mensagens, mensagem], atualizadaEm: mensagem.criadaEm }
          : c,
      ),
    }))
  }

  async function enviar(texto: string, anexo?: string) {
    const mensagem = novaMensagem({ autor: 'usuario', conteudo: texto, anexo })
    let conversaId = ativaId
    let historico: Mensagem[]

    if (conversaAtiva && conversaId) {
      historico = [...conversaAtiva.mensagens, mensagem]
      adicionarMensagem(conversaId, mensagem)
    } else {
      conversaId = crypto.randomUUID()
      historico = [mensagem]
      const nova: Conversa = {
        id: conversaId,
        titulo: tituloDe(texto),
        mensagens: historico,
        atualizadaEm: mensagem.criadaEm,
      }
      setEstado((atual) => ({ ...atual, conversas: [nova, ...atual.conversas] }))
      setAtivaId(conversaId)
    }

    setAguardandoId(conversaId)
    try {
      const resposta = await enviarMensagem(historico, { modo, anexo })
      const doAssistente = novaMensagem({ autor: 'assistente', conteudo: resposta })
      adicionarMensagem(conversaId, doAssistente)
      setDigitandoMensagemId(doAssistente.id)
    } catch {
      adicionarMensagem(
        conversaId,
        novaMensagem({
          autor: 'assistente',
          conteudo: 'Não consegui responder agora. Tente de novo em instantes.',
          erro: true,
        }),
      )
    } finally {
      setAguardandoId(null)
    }
  }

  // Trocar de conversa não deve repetir a animação de digitação da última resposta.
  function abrirConversa(id: string | null) {
    setDigitandoMensagemId(null)
    setAtivaId(id)
  }

  function excluirConversa(id: string) {
    setEstado((atual) => ({ ...atual, conversas: atual.conversas.filter((c) => c.id !== id) }))
    if (id === ativaId) setAtivaId(null)
  }

  function criarGrupo(nome: string, conversaIds: string[]) {
    const grupo: GrupoConversas = { id: crypto.randomUUID(), nome }
    setEstado((atual) => ({
      grupos: [...atual.grupos, grupo],
      conversas: atual.conversas.map((c) =>
        conversaIds.includes(c.id) ? { ...c, grupoId: grupo.id } : c,
      ),
    }))
  }

  function desfazerGrupo(grupoId: string) {
    setEstado((atual) => ({
      grupos: atual.grupos.filter((g) => g.id !== grupoId),
      conversas: atual.conversas.map((c) =>
        c.grupoId === grupoId ? { ...c, grupoId: undefined } : c,
      ),
    }))
  }

  const ocupado = aguardandoId !== null

  return (
    <>
      <div className="flex h-full gap-6">
        <div className="hidden lg:flex">
          <PainelConversas
            conversas={estado.conversas}
            grupos={estado.grupos}
            ativaId={ativaId}
            onSelecionar={abrirConversa}
            onNova={() => abrirConversa(null)}
            onExcluir={excluirConversa}
            onCriarGrupo={criarGrupo}
            onDesfazerGrupo={desfazerGrupo}
          />
        </div>

        <section className="flex min-w-0 flex-1 flex-col">
          <AnimatePresence mode="wait" initial={false}>
            {conversaAtiva ? (
              <motion.div
                key={conversaAtiva.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
                className="flex min-h-0 flex-1 flex-col"
              >
                <header className="flex items-center gap-3 border-b border-border pb-4">
                  <div className="min-w-0 flex-1">
                    <h1 className="truncate font-display text-xl font-bold text-foreground">
                      {conversaAtiva.titulo}
                    </h1>
                    {grupoAtivo && (
                      <span className="flex items-center gap-1 text-xs font-semibold text-muted-foreground">
                        <Layers className="size-3.5" aria-hidden />
                        {grupoAtivo.nome}
                      </span>
                    )}
                  </div>
                  <Button variant="secondary" size="sm" onClick={() => abrirConversa(null)}>
                    <SquarePen />
                    Novo bate-papo
                  </Button>
                </header>

                <ListaMensagens
                  mensagens={conversaAtiva.mensagens}
                  aguardando={aguardandoId === conversaAtiva.id}
                  digitandoMensagemId={digitandoMensagemId}
                />

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
                className="flex flex-1 flex-col items-center justify-center gap-6 px-4"
              >
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
