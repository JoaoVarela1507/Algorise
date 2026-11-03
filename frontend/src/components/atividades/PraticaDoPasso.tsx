import { useState } from 'react'
import { Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Carregando, ErroAoCarregar } from '@/components/ui/estados'
import { useExercicios } from '@/hooks/useAtividades'

/**
 * Exercícios de prática do passo, gerados pela IA a partir do conteúdo do
 * módulo, no nível do aluno (#201). Não contam para concluir o passo: são para
 * treinar, com a dica e a resposta a um clique.
 */
export function PraticaDoPasso({ slug, ordem }: { slug: string; ordem: number }) {
  const [pedido, setPedido] = useState(false)
  const exercicios = useExercicios(slug, ordem, pedido)

  let conteudo
  if (!pedido) {
    conteudo = (
      <Button variant="secondary" onClick={() => setPedido(true)}>
        <Sparkles aria-hidden />
        Praticar com exercícios
      </Button>
    )
  } else if (exercicios.isPending || exercicios.data?.status === 'gerando') {
    conteudo = <Carregando rotulo="Criando exercícios sobre este passo…" />
  } else if (exercicios.isError) {
    conteudo = (
      <ErroAoCarregar erro={exercicios.error} aoTentarDeNovo={() => void exercicios.refetch()} />
    )
  } else if (exercicios.data.status === 'sem_conteudo') {
    conteudo = (
      <p className="text-sm text-muted-foreground">
        Este passo ainda não tem material para gerar exercícios.
      </p>
    )
  } else if (exercicios.data.status === 'falhou') {
    conteudo = (
      <ErroAoCarregar
        erro={new Error('Não deu para criar os exercícios agora.')}
        aoTentarDeNovo={() => void exercicios.refetch()}
      />
    )
  } else {
    conteudo = (
      <ol className="flex flex-col gap-4">
        {exercicios.data.exercicios.map((exercicio, i) => (
          <li key={i} className="rounded-lg border border-border bg-card p-4 shadow-sm">
            <p className="whitespace-pre-wrap font-semibold text-foreground">
              {i + 1}. {exercicio.enunciado}
            </p>
            {exercicio.dica && (
              <details className="mt-3 text-sm">
                <summary className="cursor-pointer font-semibold text-primary">Ver dica</summary>
                <p className="mt-1 text-muted-foreground">{exercicio.dica}</p>
              </details>
            )}
            <details className="mt-2 text-sm">
              <summary className="cursor-pointer font-semibold text-primary">Ver resposta</summary>
              <pre className="mt-1 overflow-x-auto whitespace-pre-wrap rounded-md bg-muted p-3 text-foreground">
                {exercicio.resposta_esperada}
              </pre>
            </details>
          </li>
        ))}
      </ol>
    )
  }

  return (
    <section aria-labelledby="pratica" className="flex flex-col gap-3">
      <h2 id="pratica" className="font-display text-lg font-bold text-foreground">
        Pratique
      </h2>
      {conteudo}
    </section>
  )
}
