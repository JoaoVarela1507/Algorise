import { useMutation, useQuery } from '@tanstack/react-query'
import { chaves } from '@/lib/query'
import { baixarCertificado, listarCertificados, validarCertificado } from '@/services/certificados'

export function useCertificados() {
  return useQuery({ queryKey: chaves.certificados.lista(), queryFn: listarCertificados })
}

export function useValidacao(codigo: string | undefined) {
  return useQuery({
    queryKey: chaves.certificados.validacao(codigo ?? ''),
    queryFn: () => validarCertificado(codigo as string),
    enabled: Boolean(codigo?.trim()),
  })
}

export function useBaixarCertificado() {
  return useMutation({ mutationFn: baixarCertificado })
}
