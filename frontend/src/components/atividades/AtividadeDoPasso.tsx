import { Code2 } from 'lucide-react'
import { AtividadeLacunas } from '@/components/atividades/AtividadeLacunas'
import { AtividadeMultiplaEscolha } from '@/components/atividades/AtividadeMultiplaEscolha'
import { AtividadeOrdenacao } from '@/components/atividades/AtividadeOrdenacao'
import { AtividadeTerminal } from '@/components/atividades/AtividadeTerminal'
import { AtividadeTexto } from '@/components/atividades/AtividadeTexto'
import { MolduraAtividade } from '@/components/atividades/MolduraAtividade'
import type { PropsDaAtividade } from '@/components/atividades/tipos'
import { useCorrecao } from '@/hooks/useAtividades'
import type { Atividade as Roteiro } from '@/lib/terminal/roteiro'

/**
 * Escolhe a tela de cada tipo de atividade (telas 28 a 34).
 *
 * O terminal só vira terminal simulado quando há roteiro para encenar a saída;
 * sem roteiro, o comando é digitado num campo comum — a correção é a mesma,
 * no servidor.
 */
export function AtividadeDoPasso({
  roteiro,
  ...props
}: PropsDaAtividade & { roteiro: Roteiro | null }) {
  const { atividade } = props

  switch (atividade.tipo) {
    case 'terminal':
      return roteiro ? (
        <AtividadeTerminal
          atividadeId={atividade.id}
          enunciado={atividade.enunciado}
          dica={atividade.dica}
          atividade={roteiro}
          numero={props.numero}
          total={props.total}
          tempoSugeridoSegundos={atividade.tempo_sugerido_segundos}
          concluida={atividade.concluida}
          aoAvancar={props.aoAvancar}
        />
      ) : (
        <AtividadeTexto {...props} />
      )
    case 'multipla-escolha':
      return <AtividadeMultiplaEscolha {...props} />
    case 'ordenacao':
      return <AtividadeOrdenacao {...props} />
    case 'preencher-lacuna':
      return <AtividadeLacunas {...props} />
    case 'resposta-aberta':
      return <AtividadeTexto {...props} />
    case 'desafio-codigo':
      return <AtividadeDesafio {...props} />
  }
}

/**
 * Desafio de código (tela 34). O backend já corrige na sandbox (#34, rotas
 * `/desafios`), mas esta tela ainda não está ligada a ela: por enquanto a
 * atividade aparece e não trava o passo.
 */
function AtividadeDesafio({ atividade, numero, total, aoAvancar }: PropsDaAtividade) {
  const correcao = useCorrecao(atividade.id, atividade.concluida)

  return (
    <MolduraAtividade
      numero={numero}
      total={total}
      enunciado={atividade.enunciado}
      dica={atividade.dica}
      codigo={atividade.codigo}
      tempoSugeridoSegundos={atividade.tempo_sugerido_segundos}
      correcao={correcao}
      semCorrecao
      instrucao="Faça no seu computador e avance quando terminar."
      porQueBloqueado=""
      aoAvancar={aoAvancar}
    >
      <p className="flex items-start gap-3 rounded-lg border border-dashed border-border bg-card p-4 text-sm text-muted-foreground">
        <Code2 className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden />
        Escreva o programa no seu editor e rode no terminal. Quando ele funcionar com o exemplo do
        enunciado, avance.
      </p>
    </MolduraAtividade>
  )
}
