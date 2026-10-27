/**
 * Lê uma preferência do aparelho (tema, fonte, contraste, animações) no
 * formato de antes dos stores, uma chave por preferência. Hoje elas ficam no
 * `persist` de cada store; isto só serve de valor inicial, para quem já tinha
 * escolhido não perder a escolha.
 */
export function lerPreferencia<T>(chave: string, padrao: T): T {
  try {
    const salvo = localStorage.getItem(`algorise:${chave}`)
    return salvo === null ? padrao : (JSON.parse(salvo) as T)
  } catch {
    return padrao
  }
}
