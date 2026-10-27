/** Autocomplete de instituição e curso do onboarding (passo 3). */
import { useQuery } from '@tanstack/react-query'
import { useDebounce } from '@/hooks/useDebounce'
import { chaves } from '@/lib/query'
import { buscarInstituicoes, listarCursos } from '@/services/onboarding'

/** Cinco minutos: o catálogo acadêmico só muda com um seed novo. */
const CATALOGO_FRESCO = 5 * 60_000

export function useInstituicoes(busca: string) {
  const termo = useDebounce(busca.trim(), 250)
  return useQuery({
    queryKey: chaves.academico.instituicoes(termo),
    queryFn: () => buscarInstituicoes(termo),
    // Com uma letra, quase tudo casa: a lista só atrapalharia.
    enabled: termo.length >= 2,
    staleTime: CATALOGO_FRESCO,
  })
}

export function useCursos(instituicaoId: number | null) {
  return useQuery({
    queryKey: chaves.academico.cursos(instituicaoId ?? 0),
    queryFn: () => listarCursos(instituicaoId as number),
    enabled: instituicaoId !== null,
    staleTime: CATALOGO_FRESCO,
  })
}
