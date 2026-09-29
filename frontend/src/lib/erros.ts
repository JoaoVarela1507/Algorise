/** Mensagem para mostrar ao aluno a partir de um erro qualquer (em geral um `ApiError`). */
export function mensagemDeErro(erro: unknown): string {
  return erro instanceof Error && erro.message ? erro.message : 'Algo deu errado. Tente de novo.'
}
