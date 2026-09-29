/**
 * Nível do aluno a partir do XP total ("Nível 1 - 0 xp" do protótipo).
 * Regra provisória do front: 100 XP por nível, até o backend definir a curva.
 */
export const XP_POR_NIVEL = 100

export function calcularNivel(xp: number) {
  const nivel = Math.floor(xp / XP_POR_NIVEL) + 1
  const xpNoNivel = xp % XP_POR_NIVEL
  return {
    nivel,
    xpNoNivel,
    xpParaProximo: XP_POR_NIVEL - xpNoNivel,
    progresso: xpNoNivel / XP_POR_NIVEL,
  }
}
