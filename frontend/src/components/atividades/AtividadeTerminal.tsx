import { MolduraAtividade } from '@/components/atividades/MolduraAtividade'
import { TerminalSimulado } from '@/components/atividades/TerminalSimulado'
import { useCorrecao } from '@/hooks/useAtividades'
import type { Atividade } from '@/lib/terminal/roteiro'

/**
 * A atividade de terminal (telas 28 a 33): o aluno digita o comando no
 * terminal simulado e o servidor diz se acertou.
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
  const correcao = useCorrecao(atividadeId, concluida)

  return (
    <MolduraAtividade
      numero={numero}
      total={total}
      enunciado={enunciado}
      dica={dica}
      tempoSugeridoSegundos={tempoSugeridoSegundos}
      correcao={correcao}
      instrucao="Digite o comando no terminal para continuar."
      mensagemDeAcerto="Comando correto!"
      porQueBloqueado="O botão Avançar libera depois que você acertar o comando."
      aoAvancar={aoAvancar}
    >
      {/*
        O roteiro encena a saída — e tem de encenar, senão o aluno esperaria a
        rede para ver o `winget` rodar —, mas o acerto que conta, e que paga
        XP, vem da API.
      */}
      <TerminalSimulado
        atividade={atividade}
        aoExecutar={(comando) => void correcao.enviar(comando)}
      />
    </MolduraAtividade>
  )
}
