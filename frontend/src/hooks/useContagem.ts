import { useEffect, useRef, useState } from 'react'
import { animate, useReducedMotionConfig } from 'framer-motion'

/**
 * Anima um número até `alvo` (streak, XP): de 0 na primeira vez e, depois, do
 * valor anterior, para o XP ganho ao vivo (#37) subir de onde estava. Pula
 * direto pro valor se o usuário pediu menos movimento.
 */
export function useContagem(alvo: number, { duracao = 1, atraso = 0 } = {}) {
  const reduzirMovimento = useReducedMotionConfig()
  const [valor, setValor] = useState(reduzirMovimento ? alvo : 0)
  const anterior = useRef(0)

  useEffect(() => {
    const inicio = anterior.current
    anterior.current = alvo
    if (reduzirMovimento) {
      setValor(alvo)
      return
    }
    const controles = animate(inicio, alvo, {
      duration: duracao,
      delay: atraso,
      ease: 'easeOut',
      onUpdate: (atual) => setValor(Math.round(atual)),
    })
    return () => controles.stop()
  }, [alvo, duracao, atraso, reduzirMovimento])

  return valor
}
