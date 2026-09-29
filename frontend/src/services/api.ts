export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

/** Erro de uma resposta da API, com a mensagem que o backend mandou em `detail`. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    mensagem: string,
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
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
  { autenticar = true }: Opcoes = {},
): Promise<T> {
  let resposta = await enviar(path, init, autenticar)

  // Access token vencido (vale 15 minutos): renova uma vez e repete. Se a
  // renovação também falhar, o 401 sobe e quem chamou decide o que mostrar.
  if (resposta.status === 401 && autenticar && autenticador && (await autenticador.renovar())) {
    resposta = await enviar(path, init, autenticar)
  }

  if (!resposta.ok) {
    throw new ApiError(resposta.status, await lerDetalhe(resposta))
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

async function enviar(path: string, init: RequestInit, autenticar: boolean): Promise<Response> {
  const headers = new Headers(init.headers)
  const token = autenticar ? accessToken : null
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  try {
    return await fetch(`${API_URL}${path}`, { ...init, headers })
  } catch {
    // `fetch` só rejeita quando nem houve resposta: API fora ou sem rede.
    throw new ApiError(0, 'Não foi possível falar com o servidor. Tente de novo em instantes.')
  }
}

async function lerDetalhe(resposta: Response): Promise<string> {
  const padrao = 'Algo deu errado. Tente de novo.'
  try {
    const corpo = (await resposta.json()) as { detail?: unknown }
    if (typeof corpo.detail === 'string') {
      return corpo.detail
    }
    // Erro de validação do FastAPI (422): lista com uma mensagem por campo.
    if (Array.isArray(corpo.detail) && corpo.detail.length > 0) {
      const primeiro = corpo.detail[0] as { msg?: string }
      return primeiro.msg ?? padrao
    }
  } catch {
    // Corpo vazio ou que não é JSON (ex.: erro do proxy).
  }
  return padrao
}
