import { AlertCircle, Inbox, Loader2 } from 'lucide-react'
import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { mensagemDeErro } from '@/lib/erros'
import { cn } from '@/lib/utils'

/**
 * Carregando, vazio e erro — os três estados que toda tela que busca dados
 * precisa mostrar, escritos uma vez só.
 *
 * Sem isso, cada tela inventa o seu, e metade esquece o de erro: o aluno fica
 * olhando um spinner que nunca termina quando a API cai.
 */

export function Carregando({
  rotulo = 'Carregando…',
  className,
}: {
  rotulo?: string
  className?: string
}) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn('flex flex-col items-center gap-3 py-12 text-muted-foreground', className)}
    >
      <Loader2 className="size-8 animate-spin" aria-hidden />
      <p className="text-sm font-semibold">{rotulo}</p>
    </div>
  )
}

export function Vazio({
  titulo,
  descricao,
  acao,
}: {
  titulo: string
  descricao?: string
  acao?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center gap-3 py-12 text-center">
      <Inbox className="size-10 text-muted-foreground" aria-hidden />
      <p className="font-display text-lg font-bold text-foreground">{titulo}</p>
      {descricao && <p className="max-w-md text-sm text-muted-foreground">{descricao}</p>}
      {acao}
    </div>
  )
}

export function ErroAoCarregar({
  erro,
  aoTentarDeNovo,
}: {
  erro: unknown
  aoTentarDeNovo?: () => void
}) {
  return (
    // `alert` para o leitor de tela anunciar sem o aluno precisar navegar até aqui.
    <div role="alert" className="flex flex-col items-center gap-3 py-12 text-center">
      <AlertCircle className="size-10 text-destructive" aria-hidden />
      <p className="font-display text-lg font-bold text-foreground">Não deu para carregar</p>
      <p className="max-w-md text-sm text-muted-foreground">{mensagemDeErro(erro)}</p>
      {aoTentarDeNovo && (
        <Button variant="secondary" onClick={aoTentarDeNovo}>
          Tentar de novo
        </Button>
      )}
    </div>
  )
}
