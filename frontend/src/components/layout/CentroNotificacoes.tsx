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
export function CentroNotificacoes({ compacto = false }: { compacto?: boolean }) {
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
    // Compacto (barra do topo do celular), a lista se ancora na barra inteira, e
    // não no sino: ancorada nele, passava da borda esquerda da tela.
    <div ref={caixaRef} className={compacto ? undefined : 'relative'}>
      <button
        type="button"
        onClick={() => setAberto((atual) => !atual)}
        aria-expanded={aberto}
        aria-label={naoLidas ? `Notificações, ${naoLidas} não lidas` : 'Notificações'}
        className={cn(
          'flex items-center gap-2 rounded-lg font-bold text-foreground transition-colors hover:bg-accent/60',
          // No celular (barra do topo), só o sino, com o número por cima.
          compacto ? 'relative size-11 justify-center' : 'w-full px-4 py-2',
        )}
      >
        <Bell className="size-5" />
        {!compacto && 'Notificações'}
        {naoLidas > 0 && (
          <span
            className={cn(
              'rounded-full bg-primary text-xs text-primary-foreground',
              compacto ? 'absolute right-0.5 top-0.5 min-w-5 px-1 text-center' : 'ml-auto px-2',
            )}
          >
            {naoLidas > 99 ? '99+' : naoLidas}
          </span>
        )}
      </button>

      <AnimatePresence>
        {aberto && (
          <motion.div
            initial={{ opacity: 0, y: compacto ? -8 : 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: compacto ? -8 : 8 }}
            transition={{ duration: 0.15 }}
            role="dialog"
            aria-label="Notificações"
            className={cn(
              'absolute z-50 rounded-xl border border-border bg-card p-3 shadow-lg',
              // Na sidebar abre para cima; no topo do celular, para baixo, sem
              // passar da largura da tela.
              compacto ? 'inset-x-2 top-full mt-2' : 'bottom-full left-0 mb-2 w-80',
            )}
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
