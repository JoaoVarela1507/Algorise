import { useEffect, useState } from 'react'

/**
 * Espera o aluno parar de digitar antes de deixar o valor passar.
 *
 * A busca de trilhas acontece no servidor: sem isto, "redes" dispara cinco
 * requisições, e a resposta da terceira pode chegar depois da quinta.
 */
export function useDebounce<T>(valor: T, atraso = 300): T {
  const [atrasado, setAtrasado] = useState(valor)

  useEffect(() => {
    const id = setTimeout(() => setAtrasado(valor), atraso)
    return () => clearTimeout(id)
  }, [valor, atraso])

  return atrasado
}
