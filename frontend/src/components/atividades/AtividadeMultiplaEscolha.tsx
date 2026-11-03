import { Check } from 'lucide-react'
import { useState } from 'react'
import { MolduraAtividade } from '@/components/atividades/MolduraAtividade'
import { Button } from '@/components/ui/button'
import { useCorrecao } from '@/hooks/useAtividades'
import { cn } from '@/lib/utils'
import type { PropsDaAtividade } from '@/components/atividades/tipos'

/** Múltipla escolha (tela 29): marca uma alternativa e confere. */
export function AtividadeMultiplaEscolha({
  atividade,
  numero,
  total,
  aoAvancar,
}: PropsDaAtividade) {
  const correcao = useCorrecao(atividade.id, atividade.concluida)
  const [escolhida, setEscolhida] = useState<string | null>(null)
  const travada = correcao.estado === 'certa'
  const nome = `alternativas-${atividade.id}`

  return (
    <MolduraAtividade
      numero={numero}
      total={total}
      enunciado={atividade.enunciado}
      dica={atividade.dica}
      codigo={atividade.codigo}
      tempoSugeridoSegundos={atividade.tempo_sugerido_segundos}
      correcao={correcao}
      instrucao="Escolha uma alternativa e confira."
      porQueBloqueado="O botão Avançar libera depois que você acertar a alternativa."
      aoAvancar={aoAvancar}
    >
      <form
        className="flex flex-col gap-3"
        onSubmit={(evento) => {
          evento.preventDefault()
          if (escolhida) void correcao.enviar(escolhida)
        }}
      >
        <fieldset className="flex flex-col gap-2" disabled={travada}>
          <legend className="sr-only">Alternativas</legend>
          {(atividade.opcoes ?? []).map((opcao) => {
            const marcada = escolhida === opcao
            return (
              <label
                key={opcao}
                className={cn(
                  'flex cursor-pointer items-center gap-3 rounded-lg border-2 p-3 transition-colors',
                  marcada ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/40',
                  travada && 'cursor-default',
                )}
              >
                <input
                  type="radio"
                  name={nome}
                  value={opcao}
                  checked={marcada}
                  onChange={() => setEscolhida(opcao)}
                  className="sr-only"
                />
                <span
                  aria-hidden
                  className={cn(
                    'flex size-6 shrink-0 items-center justify-center rounded-full border-2',
                    marcada ? 'border-primary bg-primary text-primary-foreground' : 'border-border',
                  )}
                >
                  {marcada && <Check className="size-3.5" strokeWidth={3} />}
                </span>
                <span className="font-mono text-sm text-foreground">{opcao}</span>
              </label>
            )
          })}
        </fieldset>

        {!travada && (
          <Button
            type="submit"
            variant="secondary"
            className="self-start"
            disabled={!escolhida || correcao.enviando}
          >
            Conferir
          </Button>
        )}
      </form>
    </MolduraAtividade>
  )
}
