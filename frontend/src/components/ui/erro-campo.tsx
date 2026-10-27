/**
 * Mensagem de erro de um campo de formulário.
 *
 * O `id` vai no `aria-describedby` do campo: assim o leitor de tela lê a
 * mensagem junto com o campo quando o foco volta para ele, e não só no momento
 * em que ela aparece.
 */
export function ErroCampo({ id, mensagem }: { id: string; mensagem?: string }) {
  if (!mensagem) return null
  return (
    <p id={id} role="alert" className="text-sm text-destructive">
      {mensagem}
    </p>
  )
}
