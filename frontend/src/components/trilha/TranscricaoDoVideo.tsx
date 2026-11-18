import { useId, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ChevronDown, Captions } from 'lucide-react'
import { ErroAoCarregar } from '@/components/ui/estados'
import { useTranscricao } from '@/hooks/useTrilhas'
import { cn } from '@/lib/utils'

/**
 * A transcrição do vídeo do passo, para ler no lugar ou junto do vídeo (#21,
 * acessibilidade): quem não ouve, quem está sem fone, quem prefere ler.
 *
 * Fechada por padrão, e só busca na API quando o aluno abre. Sem transcrição
 * (o vídeo ainda não passou pelo Whisper), diz isso e lembra das legendas.
 */
export function TranscricaoDoVideo({ slug, ordem }: { slug: string; ordem: number }) {
  const [aberta, setAberta] = useState(false)
  const transcricao = useTranscricao(slug, ordem, aberta)
  const idPainel = useId()

  return (
    <div className="rounded-lg border border-border bg-card">
      <button
        type="button"
        aria-expanded={aberta}
        aria-controls={idPainel}
        onClick={() => setAberta((atual) => !atual)}
        className="flex w-full items-center gap-2 rounded-lg px-4 py-3 text-left text-sm font-bold text-foreground transition-colors hover:bg-accent/40"
      >
        <Captions className="size-5 text-primary" aria-hidden />
        <span className="flex-1">Transcrição do vídeo</span>
        <ChevronDown
          className={cn('size-5 transition-transform', aberta && 'rotate-180')}
          aria-hidden
        />
      </button>

      <AnimatePresence initial={false}>
        {aberta && (
          <motion.div
            id={idPainel}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="border-t border-border px-4 py-3"
          >
            {transcricao.isPending ? (
              <div role="status" aria-busy="true" className="flex flex-col gap-2">
                <span className="sr-only">Carregando transcrição…</span>
                {[90, 75, 85].map((largura) => (
                  <div key={largura} className="esqueleto h-4" style={{ width: `${largura}%` }} />
                ))}
              </div>
            ) : transcricao.isError ? (
              <ErroAoCarregar
                erro={transcricao.error}
                aoTentarDeNovo={() => void transcricao.refetch()}
              />
            ) : transcricao.data.falas.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Este vídeo ainda não tem transcrição. As legendas já vêm ligadas no player: use o
                botão <strong>CC</strong> dele para trocar o idioma ou desligar.
              </p>
            ) : (
              <ol className="flex max-h-72 flex-col gap-3 overflow-y-auto pr-1">
                {transcricao.data.falas.map((fala, i) => (
                  <li key={i} className="flex gap-3 text-sm leading-relaxed">
                    {fala.inicio != null && (
                      <span className="w-12 shrink-0 font-mono text-xs text-muted-foreground tabular-nums">
                        {minutos(fala.inicio)}
                      </span>
                    )}
                    <span className="text-foreground">{fala.texto}</span>
                  </li>
                ))}
              </ol>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

/** 75.4 → "1:15". */
function minutos(segundos: number): string {
  const total = Math.floor(segundos)
  const horas = Math.floor(total / 3600)
  const min = Math.floor((total % 3600) / 60)
  const seg = String(total % 60).padStart(2, '0')
  return horas ? `${horas}:${String(min).padStart(2, '0')}:${seg}` : `${min}:${seg}`
}
