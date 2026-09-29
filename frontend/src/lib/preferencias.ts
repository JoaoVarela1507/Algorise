/**
 * Preferências do aparelho (tema, fonte, contraste, animações). Ficam no
 * localStorage porque valem para o navegador, não para a conta: quem usa alto
 * contraste no notebook não necessariamente quer no celular.
 */
export function lerPreferencia<T>(chave: string, padrao: T): T {
  try {
    const salvo = localStorage.getItem(`algorise:${chave}`)
    return salvo === null ? padrao : (JSON.parse(salvo) as T)
  } catch {
    return padrao
  }
}

export function salvarPreferencia(chave: string, valor: unknown) {
  try {
    localStorage.setItem(`algorise:${chave}`, JSON.stringify(valor))
  } catch {
    // Sem armazenamento a preferência vale só até recarregar.
  }
}
