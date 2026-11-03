import { useState } from 'react'
import { MolduraAtividade } from '@/components/atividades/MolduraAtividade'
import type { PropsDaAtividade } from '@/components/atividades/tipos'
import { Button } from '@/components/ui/button'
import { useCorrecao } from '@/hooks/useAtividades'
import { cn } from '@/lib/utils'

/** O mesmo mínimo do backend (`MINIMO_RESPOSTA_ABERTA`), para avisar antes de enviar. */
const MINIMO_RESPOSTA_ABERTA = 20

/**
 * Resposta escrita: a aberta (tela 32), que fica em análise até a correção por
 * IA existir, e o comando de terminal que ainda não tem roteiro de simulação.
 */
export function AtividadeTexto({ atividade, numero, total, aoAvancar }: PropsDaAtividade) {
  const correcao = useCorrecao(atividade.id, atividade.concluida)
  const [texto, setTexto] = useState('')
  const aberta = atividade.tipo === 'resposta-aberta'
  const travada = correcao.estado === 'certa' || correcao.estado === 'em-analise'
  const curta = aberta && texto.trim().length < MINIMO_RESPOSTA_ABERTA
  const id = `resposta-${atividade.id}`

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
              <span className={cn('text-xs', curta ? 'text-muted-foreground' : 'text-success')}>
                {texto.trim().length}/{MINIMO_RESPOSTA_ABERTA} caracteres no mínimo
              </span>
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
      </form>
    </MolduraAtividade>
  )
}
