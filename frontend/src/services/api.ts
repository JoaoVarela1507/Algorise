export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

/**
 * Prefixo das rotas de negócio. Fica num lugar só: quando a API subir para a
 * v2, é esta linha que muda.
 *
 * `/health` e `/version` ficam fora dele de propósito — são de operação, e o
 * frontend não os consome.
 */
export const API_V1 = `${API_URL}/api/v1`

/**
 * Erro de uma resposta da API.
 *
 * `code` é o código estável do backend (`nao_autenticado`, `conflito`...) e é
 * nele que o código decide o que fazer; `message` é o texto em português, para
 * mostrar ao aluno. Um erro sem resposta (servidor fora) vem com status 0 e sem
 * `code`.
 */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    mensagem: string,
    readonly code?: string,
    readonly details?: Record<string, unknown>,
    readonly requestId?: string,
  ) {
    super(mensagem)
    this.name = 'ApiError'
  }
}

// O access token mora aqui, e não no `AuthContext`: o React roda os efeitos
// dos filhos antes dos do pai, então uma tela que chamasse a API ao montar (como
// o `/auth/callback`) sairia sem token se ele dependesse de um efeito do
// provider para ser registrado.
let accessToken: string | null = null

export function definirAccessToken(token: string | null) {
  accessToken = token
}

/**
 * Quem cuida da sessão (o `AuthContext`) registra aqui como renová-la, para
 * `api.ts` não importar React. Sem registro, um 401 só sobe para quem chamou.
 */
interface Autenticador {
  /** Tenta renovar a sessão; `true` se deu certo e vale repetir a chamada. */
  renovar: () => Promise<boolean>
}

let autenticador: Autenticador | null = null

export function configurarAutenticacao(novo: Autenticador | null) {
  autenticador = novo
}

interface Opcoes {
  /** Manda o access token e renova a sessão num 401. Padrão: `true`. */
  autenticar?: boolean
  /**
   * `false` manda o token mas não tenta renovar num 401. Para chamadas feitas
   * de dentro da própria renovação, que senão esperariam por si mesmas.
   */
  renovar?: boolean
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
  { autenticar = true, renovar = true }: Opcoes = {},
): Promise<T> {
  let resposta = await enviar(path, init, autenticar)

  // Access token vencido (vale 15 minutos): renova uma vez e repete. Se a
  // renovação também falhar, o 401 sobe e quem chamou decide o que mostrar.
  if (
    resposta.status === 401 &&
    autenticar &&
    renovar &&
    autenticador &&
    (await autenticador.renovar())
  ) {
    resposta = await enviar(path, init, autenticar)
  }

  if (!resposta.ok) {
    throw await lerErro(resposta)
  }

  // 204 e 202 sem corpo não têm JSON para ler.
  const texto = await resposta.text()
  return (texto ? JSON.parse(texto) : undefined) as T
}

export function apiGet<T>(path: string, opcoes?: Opcoes): Promise<T> {
  return apiFetch<T>(path, { method: 'GET' }, opcoes)
}

export function apiPost<T>(path: string, body: unknown, opcoes?: Opcoes): Promise<T> {
  return apiFetch<T>(
    path,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
    opcoes,
  )
}

export function apiPatch<T>(path: string, body: unknown, opcoes?: Opcoes): Promise<T> {
  return apiFetch<T>(
    path,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
    opcoes,
  )
}

async function enviar(path: string, init: RequestInit, autenticar: boolean): Promise<Response> {
  const headers = new Headers(init.headers)
  const token = autenticar ? accessToken : null
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  try {
    return await fetch(`${API_V1}${path}`, { ...init, headers })
  } catch {
    // `fetch` só rejeita quando nem houve resposta: API fora ou sem rede.
    throw new ApiError(0, 'Não foi possível falar com o servidor. Tente de novo em instantes.')
  }
}

async function lerErro(resposta: Response): Promise<ApiError> {
  const padrao = 'Algo deu errado. Tente de novo.'

  try {
    const corpo = (await resposta.json()) as {
      erro?: {
        code?: string
        message?: string
        details?: Record<string, unknown>
        request_id?: string
      }
      detail?: unknown
    }

    // Formato único da API (ver `backend/app/core/erros.py`).
    if (corpo.erro?.message) {
      return new ApiError(
        resposta.status,
        corpo.erro.message,
        corpo.erro.code,
        corpo.erro.details,
        corpo.erro.request_id,
      )
    }

    // Resposta que não passou pelos nossos handlers — erro do proxy, ou uma
    // rota que ainda devolva o `detail` do FastAPI.
    if (typeof corpo.detail === 'string') {
      return new ApiError(resposta.status, corpo.detail)
    }
  } catch {
    // Corpo vazio ou que não é JSON.
  }

  return new ApiError(resposta.status, padrao)
}
