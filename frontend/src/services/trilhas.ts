/**
 * Chamadas das rotas de trilha (`/api/v1/trilhas`).
 *
 * Os tipos saem do OpenAPI (`npm run gen:api`): mudar um schema no backend e
 * esquecer o frontend vira erro de compilação, não bug em produção.
 */
import { apiGet, apiPost } from '@/services/api'
import type { components } from '@/types/api'
import type { TrilhaAtual } from '@/types/ranking'
import type {
  AtividadeModulo,
  CategoriaTrilha,
  ModuloTrilha,
  StatusAtividade,
  StatusModulo,
  TipoAtividade,
  TrilhaComModulos,
  TrilhaResumo,
} from '@/types/trilha'

export type TrilhaApi = components['schemas']['Trilha']
export type TrilhaDetalheApi = components['schemas']['TrilhaDetalhe']
export type TrilhaRecomendadaApi = components['schemas']['TrilhaRecomendada']
export type TrilhaAtualApi = components['schemas']['TrilhaAtual']
export type AtividadeResumoApi = components['schemas']['AtividadeResumo']
export type PassoApi = components['schemas']['PassoDetalhe']
export type PaginaTrilhas = components['schemas']['Pagina_Trilha_']

export interface FiltrosCatalogo {
  busca?: string
  /** A tela 25 deixa marcar vários; a API aceita o parâmetro repetido. */
  periodos?: number[]
  categoria?: string
  pagina?: number
  tamanhoPagina?: number
}

function querystring(filtros: FiltrosCatalogo): string {
  const params = new URLSearchParams()
  if (filtros.busca?.trim()) params.set('busca', filtros.busca.trim())
  for (const periodo of filtros.periodos ?? []) params.append('periodo', String(periodo))
  if (filtros.categoria) params.set('categoria', filtros.categoria)
  if (filtros.pagina) params.set('pagina', String(filtros.pagina))
  if (filtros.tamanhoPagina) params.set('tamanho_pagina', String(filtros.tamanhoPagina))

  const texto = params.toString()
  return texto ? `?${texto}` : ''
}

export function buscarCatalogo(filtros: FiltrosCatalogo = {}): Promise<PaginaTrilhas> {
  return apiGet<PaginaTrilhas>(`/trilhas${querystring(filtros)}`)
}

export function buscarRecomendadas(): Promise<TrilhaRecomendadaApi[]> {
  return apiGet<TrilhaRecomendadaApi[]>('/trilhas/recomendadas')
}

/** A trilha do card da home; `null` quando não há trilha publicada. */
export function buscarTrilhaAtual(): Promise<TrilhaAtualApi | null> {
  return apiGet<TrilhaAtualApi | null>('/trilhas/atual')
}

export function paraTrilhaAtual(trilha: TrilhaAtualApi): TrilhaAtual {
  return {
    id: trilha.slug,
    nome: trilha.nome,
    disciplina: trilha.disciplina,
    periodo: trilha.periodo ?? null,
    modulosConcluidos: trilha.progresso,
    totalModulos: trilha.total_modulos,
    proximoModulo: trilha.proximo_modulo ?? null,
  }
}

export function buscarTrilha(slug: string): Promise<TrilhaDetalheApi> {
  return apiGet<TrilhaDetalheApi>(`/trilhas/${slug}`)
}

export function buscarPasso(slug: string, ordem: number): Promise<PassoApi> {
  return apiGet<PassoApi>(`/trilhas/${slug}/passos/${ordem}`)
}

export function iniciarTrilha(slug: string): Promise<TrilhaDetalheApi> {
  return apiPost<TrilhaDetalheApi>(`/trilhas/${slug}/iniciar`, {})
}

// As categorias que o card sabe colorir. Trilha com categoria nova (ou sem
// categoria) cai em "Gerais" em vez de quebrar a tela.
const CATEGORIAS: CategoriaTrilha[] = [
  'Linguagens',
  'Gerais',
  'Fundamentos',
  'Infraestrutura',
  'Dados',
]

/**
 * Converte a trilha da API para o formato que o `TrilhaCard` espera.
 *
 * As duas formas existem por motivos diferentes: a da API é o contrato, a da
 * tela é o que o componente precisa desenhar. Traduzir aqui mantém a tela livre
 * de `snake_case` e o contrato livre de detalhe de UI.
 */
export function paraCard(
  trilha: TrilhaApi | TrilhaRecomendadaApi,
  opcoes: { motivo?: string; recomendada?: boolean } = {},
): TrilhaResumo {
  const motivo = opcoes.motivo ?? ('motivo' in trilha ? trilha.motivo : '') ?? ''

  return {
    id: trilha.slug,
    nome: trilha.nome,
    categoria: CATEGORIAS.find((c) => c === trilha.categoria) ?? 'Gerais',
    periodo: trilha.periodo ?? 1,
    modulosConcluidos: trilha.progresso,
    // Trilha sem módulo ainda cadastrado dividiria por zero no card.
    totalModulos: Math.max(trilha.total_modulos, 1),
    motivo,
    recomendada: opcoes.recomendada ?? 'motivo' in trilha,
    // O desbloqueio por pré-requisito entre trilhas ainda não existe no
    // backend; hoje o que trava é o passo dentro da trilha (#29).
    bloqueada: false,
  }
}

/** Para a atividade sem tempo sugerido cadastrado. */
const MINUTOS_POR_TIPO: Record<TipoAtividade, number> = {
  'multipla-escolha': 3,
  'preencher-lacuna': 4,
  ordenacao: 4,
  terminal: 5,
  'resposta-aberta': 5,
  'desafio-codigo': 10,
}

/**
 * Converte o detalhe da API para o mapa da tela 26.
 *
 * O estado de cada passo vem pronto do servidor, que é quem decide o que está
 * liberado. Daqui só sai qual dos abertos é o "atual": o primeiro que falta.
 */
export function paraMapa(trilha: TrilhaDetalheApi): TrilhaComModulos {
  const modulos = [...(trilha.modulos ?? [])].sort((a, b) => a.ordem - b.ordem)
  const atual = modulos.find((m) => m.status === 'em-andamento')

  return {
    ...paraCard(trilha, { motivo: trilha.disciplina }),
    disciplina: trilha.disciplina,
    parceiro: trilha.parceiro_nome ?? null,
    modulos: modulos.map((modulo): ModuloTrilha => {
      const status: StatusModulo =
        modulo.status === 'concluido'
          ? 'concluido'
          : modulo.status === 'bloqueado'
            ? 'bloqueado'
            : modulo === atual
              ? 'atual'
              : 'disponivel'
      return {
        id: String(modulo.id),
        ordem: modulo.ordem,
        titulo: modulo.titulo,
        descricao: modulo.descricao ?? '',
        xp: modulo.xp ?? 0,
        status,
        atividades: paraAtividades(modulo.atividades ?? [], status),
      }
    }),
  }
}

function paraAtividades(
  atividades: AtividadeResumoApi[],
  statusDoModulo: StatusModulo,
): AtividadeModulo[] {
  const ordenadas = [...atividades].sort((a, b) => a.ordem - b.ordem)
  const proxima = ordenadas.find((a) => !a.concluida)

  return ordenadas.map((atividade) => {
    const status: StatusAtividade = atividade.concluida
      ? 'feita'
      : statusDoModulo === 'bloqueado'
        ? 'bloqueada'
        : atividade === proxima
          ? 'proxima'
          : 'pendente'
    return {
      id: String(atividade.id),
      tipo: atividade.tipo,
      titulo: atividade.enunciado,
      minutos: atividade.tempo_sugerido_segundos
        ? Math.max(1, Math.round(atividade.tempo_sugerido_segundos / 60))
        : MINUTOS_POR_TIPO[atividade.tipo],
      status,
    }
  })
}
