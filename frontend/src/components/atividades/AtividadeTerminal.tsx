import { CheckCircle2, Clock, Lightbulb } from 'lucide-react'
import { useEffect, useState } from 'react'
import { TerminalSimulado } from '@/components/atividades/TerminalSimulado'
import { useSubmeterResposta } from '@/hooks/useAtividades'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { Atividade } from '@/lib/terminal/roteiro'

/**
 * A atividade em volta do terminal (telas 28 a 33): enunciado, dica, tempo,
 * progresso e o "Avançar" que só libera depois do comando certo.
 */

export interface AtividadeTerminalProps {
  /** Id na API: é para ele que a resposta é submetida. */
  atividadeId: number
  enunciado: string
  dica?: string | null
  atividade: Atividade
  /** Posição desta atividade no passo, para a barra "1/3". */
  numero: number
  total: number
  /** Tempo sugerido; quando acaba, vira aviso — não bloqueia nada. */
  tempoSugeridoSegundos?: number | null
  /** Começa já concluída quando o aluno volta a uma atividade que já fez. */
  concluida?: boolean
  aoAvancar: () => void
}

export function AtividadeTerminal({
  atividadeId,
  enunciado,
  dica,
  atividade,
  numero,
  total,
  tempoSugeridoSegundos,
  concluida = false,
  aoAvancar,
}: AtividadeTerminalProps) {
  const [acertou, setAcertou] = useState(concluida)
  const [tentativas, setTentativas] = useState(0)
  const [mostrarDica, setMostrarDica] = useState(false)
  const submissao = useSubmeterResposta(atividadeId)

  /**
   * Quem diz se acertou é o servidor (#30). O roteiro do terminal encena a
   * saída — e tem de encenar, senão o aluno esperaria a rede para ver o
   * `winget` rodar —, mas o acerto que conta, e que paga XP, vem da API.
   */
  async function conferirNoServidor(comando: string) {
    try {
      const correcao = await submissao.mutateAsync({ conteudo: comando })
      if (correcao.correta) setAcertou(true)
      else setTentativas((n) => n + 1)
    } catch {
      // A API não respondeu: não dá para afirmar que errou, então a tentativa
      // não é contada e o aluno pode mandar de novo.
    }
  }

  return (
    <section className="flex flex-col gap-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Progresso numero={numero} total={total} />
          <span className="text-sm font-bold text-muted-foreground">
            Atividade {numero} de {total}
          </span>
        </div>
        {tempoSugeridoSegundos ? (
          <Cronometro segundos={tempoSugeridoSegundos} parado={acertou} />
        ) : null}
      </header>

      <h2 className="font-display text-xl font-bold text-foreground">{enunciado}</h2>

      {dica ? (
        <div>
          <Button variant="ghost" size="sm" onClick={() => setMostrarDica((v) => !v)}>
            <Lightbulb className="size-4" aria-hidden />
            {mostrarDica ? 'Esconder dica' : 'Ver dica'}
          </Button>
          {mostrarDica && <p className="mt-1 text-sm text-muted-foreground">{dica}</p>}
        </div>
      ) : null}

      <TerminalSimulado
        atividade={atividade}
        aoExecutar={(comando) => void conferirNoServidor(comando)}
      />

      <footer className="flex flex-wrap items-center justify-between gap-3">
        {acertou ? (
          <p className="flex items-center gap-2 text-sm font-bold text-success" role="status">
            <CheckCircle2 className="size-5" aria-hidden />
            Comando correto!
          </p>
        ) : (
          <p className="text-sm text-muted-foreground">
            {tentativas === 0
              ? 'Digite o comando no terminal para continuar.'
              : `Não foi dessa vez. Tentativas: ${tentativas}.`}
          </p>
        )}

        <Button
          size="lg"
          disabled={!acertou || submissao.isPending}
          onClick={aoAvancar}
          // O botão desabilitado some do leitor de tela; o texto acima diz o
          // que falta, e isto explica o porquê de ele não responder.
          aria-describedby={acertou ? undefined : 'por-que-bloqueado'}
        >
          Avançar
        </Button>
        {!acertou && (
          <span id="por-que-bloqueado" className="sr-only">
            O botão Avançar libera depois que você acertar o comando.
          </span>
        )}
      </footer>
    </section>
  )
}

function Progresso({ numero, total }: { numero: number; total: number }) {
  return (
    <div
      className="flex gap-1"
      role="progressbar"
      aria-valuenow={numero}
      aria-valuemin={1}
      aria-valuemax={total}
      aria-label={`Atividade ${numero} de ${total}`}
    >
      {Array.from({ length: total }, (_, indice) => (
        <span
          key={indice}
          className={cn(
            'h-2 w-8 rounded-full transition-colors',
            indice < numero ? 'bg-primary' : 'bg-muted',
          )}
        />
      ))}
    </div>
  )
}

/**
 * Tempo sugerido, contando para trás.
 *
 * Chegar a zero não bloqueia nem reprova: a atividade não é prova, e um
 * cronômetro que trava a tela só serviria para desistir. Ele vira um aviso.
 */
function Cronometro({ segundos, parado }: { segundos: number; parado: boolean }) {
  const [restante, setRestante] = useState(segundos)

  useEffect(() => {
    if (parado) return
    const id = setInterval(() => setRestante((atual) => Math.max(atual - 1, 0)), 1000)
    return () => clearInterval(id)
  }, [parado])

  const estourou = restante === 0

  return (
    <p
      className={cn(
        'flex items-center gap-1.5 text-sm font-bold',
        estourou ? 'text-streak' : 'text-muted-foreground',
      )}
      // `off`: o cronômetro mudando a cada segundo atropelaria o leitor de tela.
      aria-live="off"
    >
      <Clock className="size-4" aria-hidden />
      {estourou ? 'Sem pressa, continue' : `${formatar(restante)} sugeridos`}
    </p>
  )
}

function formatar(segundos: number): string {
  const minutos = Math.floor(segundos / 60)
  const resto = segundos % 60
  return `${minutos}:${String(resto).padStart(2, '0')}`
}
