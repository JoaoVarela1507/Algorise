import { useState } from 'react'
import { motion } from 'framer-motion'
import { Mic } from 'lucide-react'
import { FeedbackDoPolvo } from '@/components/atividades/FeedbackDoPolvo'
import { MolduraAtividade } from '@/components/atividades/MolduraAtividade'
import type { PropsDaAtividade } from '@/components/atividades/tipos'
import { Button } from '@/components/ui/button'
import { useCorrecao } from '@/hooks/useAtividades'
import { useDitado } from '@/hooks/useDitado'
import { cn } from '@/lib/utils'

/** O mesmo mínimo do backend (`MINIMO_RESPOSTA_ABERTA`), para avisar antes de enviar. */
const MINIMO_RESPOSTA_ABERTA = 20

/**
 * Resposta escrita: a aberta (tela 32), corrigida pela IA com o retorno do
 * polvo (#22), e o comando de terminal que ainda não tem roteiro de simulação.
 */
export function AtividadeTexto({ atividade, numero, total, aoAvancar }: PropsDaAtividade) {
  const correcao = useCorrecao(atividade.id, atividade.concluida)
  const [texto, setTexto] = useState('')
  const aberta = atividade.tipo === 'resposta-aberta'
  // Em análise (a IA não respondeu) o texto continua editável: o aluno pode
  // seguir pelo Avançar ou mandar de novo quando a IA voltar.
  const travada = correcao.estado === 'certa'
  const curta = aberta && texto.trim().length < MINIMO_RESPOSTA_ABERTA
  const id = `resposta-${atividade.id}`
  // Ditado por voz (#22): o que foi falado entra no fim do texto, que continua
  // editável — o reconhecimento erra termos técnicos, e o aluno corrige antes de enviar.
  const { ouvindo, suportado, alternar } = useDitado((falado) =>
    setTexto((atual) => (atual.trim() ? `${atual.trimEnd()} ${falado.trim()}` : falado.trim())),
  )

  return (
    <MolduraAtividade
      numero={numero}
      total={total}
      enunciado={atividade.enunciado}
      dica={atividade.dica}
      codigo={atividade.codigo}
      tempoSugeridoSegundos={atividade.tempo_sugerido_segundos}
      correcao={correcao}
      instrucao={aberta ? 'Escreva sua resposta e envie.' : 'Digite o comando e confira.'}
      mensagemDeAcerto={aberta ? undefined : 'Comando correto!'}
      porQueBloqueado="O botão Avançar libera depois que você enviar a resposta."
      feedbackNoExercicio={aberta}
      aoAvancar={aoAvancar}
    >
      <form
        className="flex flex-col gap-2"
        onSubmit={(evento) => {
          evento.preventDefault()
          if (texto.trim() && !curta) void correcao.enviar(texto)
        }}
      >
        <label htmlFor={id} className="sr-only">
          {aberta ? 'Sua resposta' : 'Comando'}
        </label>
        {aberta ? (
          <textarea
            id={id}
            value={texto}
            onChange={(evento) => setTexto(evento.target.value)}
            disabled={travada}
            rows={5}
            placeholder="Explique com suas palavras…"
            className="rounded-lg border border-border bg-card p-3 text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        ) : (
          <input
            id={id}
            value={texto}
            onChange={(evento) => setTexto(evento.target.value)}
            disabled={travada}
            autoComplete="off"
            spellCheck={false}
            placeholder="Digite o comando"
            className="rounded-lg border border-border bg-card px-3 py-2 font-mono text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        )}

        {!travada && (
          <div className="flex items-center justify-between gap-3">
            {aberta ? (
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={alternar}
                  disabled={!suportado}
                  aria-pressed={ouvindo}
                  aria-label={ouvindo ? 'Parar ditado' : 'Responder por voz'}
                  title={
                    suportado
                      ? 'Responder por voz'
                      : 'Ditado por voz não é suportado neste navegador'
                  }
                  className={cn(
                    'relative flex size-11 shrink-0 items-center justify-center rounded-full border border-border transition-colors disabled:cursor-not-allowed disabled:opacity-40',
                    ouvindo
                      ? 'border-destructive bg-destructive text-destructive-foreground'
                      : 'text-primary hover:bg-accent/60',
                  )}
                >
                  {ouvindo && (
                    <motion.span
                      aria-hidden
                      className="absolute inset-0 rounded-full bg-destructive"
                      animate={{ scale: [1, 1.5], opacity: [0.5, 0] }}
                      transition={{ duration: 1.2, repeat: Infinity }}
                    />
                  )}
                  <Mic className="relative size-5" />
                </button>
                <span
                  className={cn('text-xs', curta ? 'text-muted-foreground' : 'text-success')}
                  aria-live="polite"
                >
                  {ouvindo
                    ? 'Ouvindo… fale sua resposta'
                    : `${texto.trim().length}/${MINIMO_RESPOSTA_ABERTA} caracteres no mínimo`}
                </span>
              </div>
            ) : (
              <span />
            )}
            <Button
              type="submit"
              variant="secondary"
              disabled={!texto.trim() || curta || correcao.enviando}
            >
              {aberta ? 'Enviar' : 'Conferir'}
            </Button>
          </div>
        )}

        {aberta && <FeedbackDoPolvo correcao={correcao} />}
      </form>
    </MolduraAtividade>
  )
}
