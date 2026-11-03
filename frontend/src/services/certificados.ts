/**
 * Certificados das trilhas de parceiros (tela 20) e a validação pública (#32).
 */
import { apiGet, apiResposta } from '@/services/api'
import type { components } from '@/types/api'

export type PeriodoDeCertificados = components['schemas']['PeriodoDeCertificados']
export type ItemDeCertificado = components['schemas']['ItemDeCertificado']
export type ValidacaoDeCertificado = components['schemas']['Validacao']

export function listarCertificados(): Promise<PeriodoDeCertificados[]> {
  return apiGet<PeriodoDeCertificados[]>('/certificados')
}

/** Pública: quem confere o certificado não precisa de conta. */
export function validarCertificado(codigo: string): Promise<ValidacaoDeCertificado> {
  return apiGet<ValidacaoDeCertificado>(
    `/certificados/validar/${encodeURIComponent(codigo.trim())}`,
    { autenticar: false },
  )
}

/** Baixa o PDF: a rota exige o token, então não dá para ser um link comum. */
export async function baixarCertificado(certificadoId: number): Promise<void> {
  const resposta = await apiResposta(`/certificados/${certificadoId}/download`)
  const nome =
    resposta.headers.get('content-disposition')?.match(/filename="([^"]+)"/)?.[1] ??
    'certificado.pdf'
  const url = URL.createObjectURL(await resposta.blob())
  const link = document.createElement('a')
  link.href = url
  link.download = nome
  link.click()
  URL.revokeObjectURL(url)
}
