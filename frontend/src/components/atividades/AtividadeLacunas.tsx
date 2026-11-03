import { Fragment, useRef, useState } from 'react'
import { MolduraAtividade } from '@/components/atividades/MolduraAtividade'
import type { PropsDaAtividade } from '@/components/atividades/tipos'
import { Button } from '@/components/ui/button'
import { useCorrecao } from '@/hooks/useAtividades'
import { cn } from '@/lib/utils'

/** O marcador de buraco no `codigo` da atividade. */
const LACUNA = '___'

/**
 * Preencher lacunas (tela 31): o trecho de código vem com `___` nos buracos.
 * Com banco de palavras, clicar numa preenche o buraco em foco (ou o próximo
 * vazio); sem banco, o aluno digita.
 */
export function AtividadeLacunas({ atividade, numero, total, aoAvancar }: PropsDaAtividade) {
  const correcao = useCorrecao(atividade.id, atividade.concluida)
  const partes = (atividade.codigo ?? '').split(LACUNA)
  const buracos = partes.length - 1
  const [respostas, setRespostas] = useState<string[]>(() => Array(buracos).fill(''))
  const emFoco = useRef<number | null>(null)
  const campos = useRef<(HTMLInputElement | null)[]>([])
  const travada = correcao.estado === 'certa'
  const completo = respostas.every((r) => r.trim() !== '')

  function preencher(indice: number, valor: string) {
    setRespostas((atuais) => atuais.map((r, i) => (i === indice ? valor : r)))
  }

  function usarPalavra(palavra: string) {
    const alvo = emFoco.current ?? respostas.findIndex((r) => r.trim() === '')
    if (alvo < 0) return
    preencher(alvo, palavra)
    // Segue para o próximo buraco vazio, como quem vai completando a frase.
    const proximo = respostas.findIndex((r, i) => i !== alvo && r.trim() === '')
    emFoco.current = proximo >= 0 ? proximo : null
    if (proximo >= 0) campos.current[proximo]?.focus()
  }

  return (
    <MolduraAtividade
      numero={numero}
      total={total}
      enunciado={atividade.enunciado}
      dica={atividade.dica}
      tempoSugeridoSegundos={atividade.tempo_sugerido_segundos}
      correcao={correcao}
      instrucao="Preencha as lacunas e confira."
      porQueBloqueado="O botão Avançar libera depois que você acertar todas as lacunas."
      aoAvancar={aoAvancar}
    >
      <form
        className="flex flex-col gap-3"
        onSubmit={(evento) => {
          evento.preventDefault()
          if (completo) void correcao.enviar(JSON.stringify(respostas))
        }}
      >
        <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg border border-border bg-[#11161d] p-4 font-mono text-sm leading-9 text-[#e6edf3]">
          {partes.map((parte, i) => (
            <Fragment key={i}>
              {parte}
              {i < buracos && (
                <input
                  ref={(campo) => {
                    campos.current[i] = campo
                  }}
                  value={respostas[i]}
                  onChange={(evento) => preencher(i, evento.target.value)}
                  onFocus={() => (emFoco.current = i)}
                  disabled={travada}
                  aria-label={`Lacuna ${i + 1} de ${buracos}`}
                  autoComplete="off"
                  spellCheck={false}
                  size={Math.max(respostas[i].length, 4)}
                  className={cn(
                    'mx-0.5 rounded border-b-2 bg-white/10 px-1.5 py-0.5 text-center font-mono text-sm text-[#ffd479] outline-none',
                    'border-[#ffd479]/60 focus:border-[#ffd479] focus:bg-white/15',
                    travada && 'border-success text-success',
                  )}
                />
              )}
            </Fragment>
          ))}
        </pre>

        {!travada && atividade.opcoes && atividade.opcoes.length > 0 && (
          <div className="flex flex-wrap gap-2" aria-label="Banco de palavras">
            {atividade.opcoes.map((palavra) => (
              <button
                key={palavra}
                type="button"
                // Sem roubar o foco do buraco: é ele que diz onde a palavra entra.
                onMouseDown={(evento) => evento.preventDefault()}
                onClick={() => usarPalavra(palavra)}
                className="rounded-lg border-2 border-border bg-card px-3 py-1.5 font-mono text-sm font-semibold text-foreground transition-colors hover:border-primary/50 hover:bg-primary/5"
              >
                {palavra}
              </button>
            ))}
          </div>
        )}

        {!travada && (
          <Button
            type="submit"
            variant="secondary"
            className="self-start"
            disabled={!completo || correcao.enviando}
          >
            Conferir
          </Button>
        )}
      </form>
    </MolduraAtividade>
  )
}
