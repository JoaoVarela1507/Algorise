import { useEffect, useState } from 'react'
import { animate, useReducedMotionConfig } from 'framer-motion'

/** Anima um número de 0 até `alvo` (streak, XP). Pula direto pro valor se o usuário pediu menos movimento. */
export function useContagem(alvo: number, { duracao = 1, atraso = 0 } = {}) {
  const reduzirMovimento = useReducedMotionConfig()
  const [valor, setValor] = useState(reduzirMovimento ? alvo : 0)

  useEffect(() => {
    if (reduzirMovimento) {
      setValor(alvo)
      return
    }
    const controles = animate(0, alvo, {
      duration: duracao,
      delay: atraso,
      ease: 'easeOut',
      onUpdate: (atual) => setValor(Math.round(atual)),
    })
    return () => controles.stop()
  }, [alvo, duracao, atraso, reduzirMovimento])

  return valor
}
