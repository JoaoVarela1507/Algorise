/**
 * Onboarding acadêmico pela API (#28): autocomplete, conclusão e ementa.
 *
 * Instituição e curso viajam de um de dois jeitos: pelo `id`, quando o aluno
 * escolheu uma sugestão, ou pelo nome, quando digitou algo fora do catálogo. O
 * backend aceita os dois e recusa os dois ao mesmo tempo, então quem monta o
 * corpo é `corpoDoOnboarding`, num lugar só.
 */
import { apiFetch, apiGet, apiPost } from '@/services/api'
import { perfilParaUsuario, type PerfilApi } from '@/services/auth'
import type { components } from '@/types/api'
import type { NivelExperiencia, TipoTrilha, Usuario } from '@/types/usuario'

export type Instituicao = components['schemas']['InstituicaoResumo']
export type Curso = components['schemas']['CursoResumo']
export type EmentaStatus = components['schemas']['EmentaStatus']

/** Um campo do autocomplete: o texto na tela e, se veio de uma sugestão, o id. */
export interface Escolha {
  texto: string
  id: number | null
}

export interface DadosOnboarding {
  nivelExperiencia: NivelExperiencia
  tipoTrilha: TipoTrilha
  instituicao: Escolha
  curso: Escolha
  periodo?: number
}

export function buscarInstituicoes(busca: string): Promise<Instituicao[]> {
  const parametros = new URLSearchParams({ busca })
  return apiGet<Instituicao[]>(`/instituicoes?${parametros}`, { autenticar: false })
}

export function listarCursos(instituicaoId: number): Promise<Curso[]> {
  return apiGet<Curso[]>(`/instituicoes/${instituicaoId}/cursos`, { autenticar: false })
}

export function corpoDoOnboarding(dados: DadosOnboarding) {
  const instituicao = dados.instituicao.texto.trim()
  const curso = dados.curso.texto.trim()
  return {
    nivel_experiencia: dados.nivelExperiencia,
    tipo_trilha: dados.tipoTrilha,
    instituicao_id: dados.instituicao.id ?? undefined,
    instituicao: dados.instituicao.id === null && instituicao ? instituicao : undefined,
    curso_id: dados.curso.id ?? undefined,
    // Curso digitado só faz sentido com alguma instituição informada.
    curso:
      dados.curso.id === null && curso && (dados.instituicao.id !== null || instituicao)
        ? curso
        : undefined,
    periodo: dados.periodo,
  }
}

export async function concluirOnboarding(dados: DadosOnboarding): Promise<Usuario> {
  return perfilParaUsuario(await apiPost<PerfilApi>('/onboarding', corpoDoOnboarding(dados)))
}

/** Sobe o PDF. O texto é lido depois, no servidor: a resposta vem com `pendente`. */
export async function enviarEmenta(arquivo: File): Promise<EmentaStatus> {
  const corpo = new FormData()
  corpo.append('arquivo', arquivo)
  return apiFetch<EmentaStatus>('/ementas', { method: 'POST', body: corpo })
}
