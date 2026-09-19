const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`)
  if (!response.ok) {
    throw new Error(`Erro ao buscar ${path}: ${response.status}`)
  }
  return response.json()
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    throw new Error(`Erro ao enviar para ${path}: ${response.status}`)
  }
  return response.json()
}
