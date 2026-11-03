import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Bell, CheckCheck } from 'lucide-react'
import { tempoRelativo } from '@/lib/tempo'
import { cn } from '@/lib/utils'
import {
  useMarcarLida,
  useMarcarTodasLidas,
  useNaoLidas,
  useNotificacoes,
} from '@/hooks/useNotificacoes'

/**
 * O sino da sidebar (#37): quantas faltam ler e a lista do que chegou, inclusive
 * com o aluno offline. Ao vivo, o número sobe pelo WebSocket.
 */
export function CentroNotificacoes() {
  const [aberto, setAberto] = useState(false)
  const caixaRef = useRef<HTMLDivElement>(null)
  const naoLidas = useNaoLidas().data ?? 0
  const lista = useNotificacoes(aberto)
  const marcarLida = useMarcarLida()
  const marcarTodas = useMarcarTodasLidas()

  useEffect(() => {
    if (!aberto) return
    function fora(evento: MouseEvent) {
      if (!caixaRef.current?.contains(evento.target as Node)) setAberto(false)
    }
    function esc(evento: KeyboardEvent) {
      if (evento.key === 'Escape') setAberto(false)
    }
    document.addEventListener('mousedown', fora)
    document.addEventListener('keydown', esc)
    return () => {
      document.removeEventListener('mousedown', fora)
      document.removeEventListener('keydown', esc)
    }
  }, [aberto])

  return (
    <div ref={caixaRef} className="relative">
      <button
        type="button"
        onClick={() => setAberto((atual) => !atual)}
        aria-expanded={aberto}
        aria-label={naoLidas ? `Notificações, ${naoLidas} não lidas` : 'Notificações'}
        className="flex w-full items-center gap-2 rounded-lg px-4 py-2 font-bold text-foreground transition-colors hover:bg-accent/60"
      >
        <Bell className="size-5" />
        Notificações
        {naoLidas > 0 && (
          <span className="ml-auto rounded-full bg-primary px-2 text-xs text-primary-foreground">
            {naoLidas > 99 ? '99+' : naoLidas}
          </span>
        )}
      </button>

      <AnimatePresence>
        {aberto && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ duration: 0.15 }}
            role="dialog"
            aria-label="Notificações"
            className="absolute bottom-full left-0 z-50 mb-2 w-80 rounded-xl border border-border bg-card p-3 shadow-lg"
          >
            <div className="mb-2 flex items-center justify-between">
              <h2 className="font-display font-bold text-card-foreground">Notificações</h2>
              {naoLidas > 0 && (
                <button
                  type="button"
                  onClick={() => marcarTodas.mutate()}
                  className="flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
                >
                  <CheckCheck className="size-4" />
                  Marcar todas como lidas
                </button>
              )}
            </div>

            {lista.isLoading ? (
              <p className="py-6 text-center text-sm text-muted-foreground">Carregando…</p>
            ) : !lista.data?.itens.length ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                Nenhuma notificação por enquanto.
              </p>
            ) : (
              <ul className="flex max-h-80 flex-col gap-1 overflow-y-auto">
                {lista.data.itens.map((notificacao) => (
                  <li key={notificacao.id}>
                    <button
                      type="button"
                      onClick={() => !notificacao.lida_em && marcarLida.mutate(notificacao.id)}
                      className={cn(
                        'w-full rounded-lg px-3 py-2 text-left transition-colors hover:bg-accent/60',
                        !notificacao.lida_em && 'bg-accent/40',
                      )}
                    >
                      <span className="flex items-center gap-2 text-sm font-bold text-card-foreground">
                        {!notificacao.lida_em && (
                          <span className="size-2 rounded-full bg-primary" aria-label="Não lida" />
                        )}
                        {notificacao.titulo}
                      </span>
                      <span className="block text-sm text-muted-foreground">
                        {notificacao.mensagem}
                      </span>
                      <span className="block text-xs text-muted-foreground">
                        {tempoRelativo(new Date(notificacao.criado_em).getTime())}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
