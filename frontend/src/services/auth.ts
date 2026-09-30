/**
 * Autenticação contra a API (`/auth/*`) e onde os tokens ficam guardados.
 *
 * - access token: só em memória. Vale 15 minutos e some ao recarregar a página;
 *   quem traz a sessão de volta é o refresh.
 * - refresh token: no `localStorage` com "manter-se conectado" (sobrevive a
 *   fechar o navegador) e no `sessionStorage` sem (morre com a aba).
 */
import {
  API_V1,
  ApiError,
  apiFetch,
  apiGet,
  apiPatch,
  apiPost,
  definirAccessToken,
} from '@/services/api'
import type { AtualizacaoPerfil, NivelExperiencia, TipoTrilha, Usuario } from '@/types/usuario'

export type Provedor = 'github' | 'google'

interface UsuarioApi {
  id: number
  email: string
  username: string
  nome_exibicao: string
  avatar_url: string | null
  xp_total: number
  tem_senha: boolean
}

interface SessaoApi {
  access_token: string
  refresh_token: string
  expira_em: number
  usuario: UsuarioApi
  /** Recado do backend, como "a exclusão da sua conta foi cancelada". */
  aviso?: string | null
}

const CHAVE_REFRESH = 'algorise:refresh'

function guardarSessao(
  sessao: Pick<SessaoApi, 'access_token' | 'refresh_token'>,
  lembrar: boolean,
) {
  definirAccessToken(sessao.access_token)
  const destino = lembrar ? localStorage : sessionStorage
  const outro = lembrar ? sessionStorage : localStorage
  destino.setItem(CHAVE_REFRESH, sessao.refresh_token)
  outro.removeItem(CHAVE_REFRESH)
}

function lerRefresh(): { token: string; lembrar: boolean } | null {
  const lembrado = localStorage.getItem(CHAVE_REFRESH)
  if (lembrado) return { token: lembrado, lembrar: true }
  const daAba = sessionStorage.getItem(CHAVE_REFRESH)
  return daAba ? { token: daAba, lembrar: false } : null
}

export function temSessaoGuardada() {
  return lerRefresh() !== null
}

export function limparSessao() {
  definirAccessToken(null)
  localStorage.removeItem(CHAVE_REFRESH)
  sessionStorage.removeItem(CHAVE_REFRESH)
}

// --- chamadas ---------------------------------------------------------------

export async function entrar(
  email: string,
  senha: string,
  lembrar: boolean,
): Promise<{ usuario: Usuario; aviso?: string }> {
  const sessao = await apiPost<SessaoApi>(
    '/auth/login',
    { email, senha, lembrar },
    { autenticar: false },
  )
  guardarSessao(sessao, lembrar)
  return { usuario: await completarPerfil(sessao.usuario), aviso: sessao.aviso ?? undefined }
}

export async function cadastrar(dados: {
  username: string
  email: string
  senha: string
}): Promise<Usuario> {
  const sessao = await apiPost<SessaoApi>(
    '/auth/register',
    // O formulário da tela 6 não pede nome de exibição: começa como o username.
    // `aceite_termos`: o checkbox é obrigatório no formulário, e o backend
    // registra o aceite (LGPD).
    { ...dados, nome_exibicao: dados.username, aceite_termos: true },
    { autenticar: false },
  )
  guardarSessao(sessao, false)
  return completarPerfil(sessao.usuario)
}

let renovacaoEmAndamento: Promise<Usuario | null> | null = null

/**
 * Troca o refresh guardado por um par novo e devolve o aluno, ou `null` se a
 * sessão acabou.
 *
 * Chamadas simultâneas compartilham a mesma renovação. Isso importa porque o
 * backend gasta o refresh a cada uso: dois pedidos em paralelo com o mesmo
 * token fariam o segundo falhar e derrubar o aluno. (Também cobre o
 * `StrictMode`, que roda o efeito de montagem duas vezes em desenvolvimento.)
 */
export function renovarSessao(): Promise<Usuario | null> {
  renovacaoEmAndamento ??= renovar().finally(() => {
    renovacaoEmAndamento = null
  })
  return renovacaoEmAndamento
}

async function renovar(): Promise<Usuario | null> {
  const guardado = lerRefresh()
  if (!guardado) return null

  try {
    const sessao = await apiPost<SessaoApi>(
      '/auth/refresh',
      { refresh_token: guardado.token },
      { autenticar: false },
    )
    guardarSessao(sessao, guardado.lembrar)
    return completarPerfil(sessao.usuario)
  } catch (erro) {
    // Outra aba pode ter renovado primeiro e gastado este token. Se o
    // guardado mudou nesse meio-tempo, vale tentar com o novo.
    const atual = lerRefresh()
    if (
      erro instanceof ApiError &&
      erro.status === 401 &&
      atual &&
      atual.token !== guardado.token
    ) {
      return renovar()
    }
    if (erro instanceof ApiError && erro.status === 401) {
      limparSessao()
    }
    // Servidor fora (0) ou 503: a sessão pode estar boa, só não deu para
    // confirmar agora. Não apaga o refresh.
    return null
  }
}

export async function sair() {
  const guardado = lerRefresh()
  limparSessao()
  if (guardado) {
    // Melhor esforço: a sessão local já acabou, mesmo que a API esteja fora.
    await apiPost('/auth/logout', { refresh_token: guardado.token }, { autenticar: false }).catch(
      () => undefined,
    )
  }
}

/** Fim do login social: a API devolveu o par no fragmento da URL. */
export async function concluirLoginSocial(tokens: {
  access_token: string
  refresh_token: string
}): Promise<Usuario> {
  // O backend abre a sessão do login social sempre como "manter-se conectado".
  guardarSessao(tokens, true)
  const usuario = await apiGet<UsuarioApi>('/auth/eu')
  return completarPerfil(usuario)
}

/**
 * Manda o navegador para o provedor.
 *
 * Antes, confere se ele está configurado: sem as credenciais no backend, a rota
 * responde 503 em JSON, e navegar direto deixaria o aluno olhando um JSON cru.
 * Com `redirect: 'manual'` o redirecionamento para o GitHub não é seguido; ele
 * só aparece como `opaqueredirect`, que é o sinal de que está tudo certo.
 */
export async function iniciarLoginSocial(provedor: Provedor) {
  const url = `${API_V1}/auth/${provedor}/login`

  let resposta: Response
  try {
    resposta = await fetch(url, { redirect: 'manual' })
  } catch {
    throw new ApiError(0, 'Não foi possível falar com o servidor. Tente de novo em instantes.')
  }

  if (resposta.type !== 'opaqueredirect' && !resposta.ok) {
    const nome = provedor === 'github' ? 'GitHub' : 'Google'
    throw new ApiError(resposta.status, `O login com ${nome} ainda não está disponível.`)
  }

  window.location.assign(url)
}

export async function solicitarRedefinicao(email: string) {
  await apiPost('/auth/esqueci-senha', { email }, { autenticar: false })
}

export async function redefinirSenha(token: string, senha: string) {
  await apiPost('/auth/redefinir-senha', { token, senha }, { autenticar: false })
}

// --- dados da conta (LGPD) -------------------------------------------------

/** Baixa o JSON com tudo o que o Algorise guarda sobre o aluno. */
export async function baixarMeusDados() {
  const dados = await apiGet<unknown>('/usuarios/me/dados')
  const arquivo = new Blob([JSON.stringify(dados, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(arquivo)
  const link = document.createElement('a')
  link.href = url
  link.download = 'algorise-meus-dados.json'
  link.click()
  URL.revokeObjectURL(url)
}

/** Pede a exclusão da conta. Devolve a data em que os dados serão apagados. */
export async function excluirConta(dados: { confirmacao: string; senha?: string }) {
  const resposta = await apiFetch<{ exclusao_agendada_para: string }>('/usuarios/me', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ confirmacao: dados.confirmacao, senha: dados.senha || null }),
  })
  // O backend já derrubou as sessões; aqui só some o que ficou no navegador.
  limparSessao()
  return new Date(resposta.exclusao_agendada_para)
}

// --- perfil -----------------------------------------------------------------

/** Formato do `/usuarios/me`: o `UsuarioApi` mais o que o onboarding coleta. */
interface PerfilApi extends UsuarioApi {
  streak_dias: number
  nivel_experiencia: NivelExperiencia
  tipo_trilha: TipoTrilha
  instituicao: string | null
  curso: string | null
  periodo: number | null
}

function perfilParaUsuario(api: PerfilApi): Usuario {
  return {
    id: String(api.id),
    nome: api.nome_exibicao,
    username: api.username,
    email: api.email,
    avatarUrl: api.avatar_url ?? undefined,
    temSenha: api.tem_senha,
    xp: api.xp_total,
    streakDias: api.streak_dias,
    nivelExperiencia: api.nivel_experiencia,
    tipoTrilha: api.tipo_trilha,
    instituicao: api.instituicao ?? undefined,
    curso: api.curso ?? undefined,
    periodo: api.periodo ?? undefined,
  }
}

/**
 * O login devolve só o básico do aluno; o perfil completo (onboarding e
 * streak) vem do `/usuarios/me`. Se essa rota falhar, segue com o básico e o
 * perfil guardado no navegador, para o login não depender dela.
 */
async function completarPerfil(basico: UsuarioApi): Promise<Usuario> {
  try {
    // Sem renovar: esta chamada também roda de dentro da renovação da sessão.
    return perfilParaUsuario(await apiGet<PerfilApi>('/usuarios/me', { renovar: false }))
  } catch {
    return paraUsuario(basico)
  }
}

export async function atualizarPerfil(dados: AtualizacaoPerfil): Promise<Usuario> {
  const perfil = await apiPatch<PerfilApi>('/usuarios/me', {
    nome_exibicao: dados.nome,
    nivel_experiencia: dados.nivelExperiencia,
    tipo_trilha: dados.tipoTrilha,
    instituicao: dados.instituicao,
    curso: dados.curso,
    periodo: dados.periodo,
  })
  return perfilParaUsuario(perfil)
}

/**
 * Reserva para quando o `/usuarios/me` não responde (e para o login de teste,
 * que não tem token): o que o onboarding coletou fica neste navegador, por
 * aluno, para não se perder a cada recarga.
 */
type PerfilLocal = Pick<
  Usuario,
  'nivelExperiencia' | 'tipoTrilha' | 'instituicao' | 'curso' | 'periodo'
>

const chavePerfil = (id: string) => `algorise:perfil:${id}`

export function guardarPerfilLocal(usuario: Usuario) {
  const perfil: PerfilLocal = {
    nivelExperiencia: usuario.nivelExperiencia,
    tipoTrilha: usuario.tipoTrilha,
    instituicao: usuario.instituicao,
    curso: usuario.curso,
    periodo: usuario.periodo,
  }
  localStorage.setItem(chavePerfil(usuario.id), JSON.stringify(perfil))
}

function lerPerfilLocal(id: string): Partial<PerfilLocal> {
  try {
    return JSON.parse(localStorage.getItem(chavePerfil(id)) ?? '{}') as Partial<PerfilLocal>
  } catch {
    return {}
  }
}

function paraUsuario(api: UsuarioApi): Usuario {
  const id = String(api.id)
  const perfil = lerPerfilLocal(id)
  return {
    id,
    nome: api.nome_exibicao,
    username: api.username,
    email: api.email,
    avatarUrl: api.avatar_url ?? undefined,
    temSenha: api.tem_senha,
    xp: api.xp_total,
    // O streak entra quando a API passar a devolvê-lo.
    streakDias: 0,
    nivelExperiencia: perfil.nivelExperiencia ?? ('baixo' satisfies NivelExperiencia),
    tipoTrilha: perfil.tipoTrilha ?? ('guiada' satisfies TipoTrilha),
    instituicao: perfil.instituicao,
    curso: perfil.curso,
    periodo: perfil.periodo,
  }
}
