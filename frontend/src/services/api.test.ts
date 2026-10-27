/**
 * Testes da camada de API.
 *
 * É o ponto por onde passa toda conversa com o backend: se ela ler o erro
 * errado, o aluno vê "Algo deu errado" no lugar de "E-mail ou senha
 * incorretos", e um 401 deixa de renovar a sessão.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  ApiError,
  apiGet,
  apiPost,
  configurarAutenticacao,
  definirAccessToken,
} from '@/services/api'

function respostaJson(corpo: unknown, status = 200) {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

beforeEach(() => {
  definirAccessToken(null)
  configurarAutenticacao(null)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('caminho feliz', () => {
  it('chama o prefixo /api/v1 e devolve o corpo', async () => {
    const fetchFalso = vi.fn().mockResolvedValue(respostaJson({ total: 7 }))
    vi.stubGlobal('fetch', fetchFalso)

    await expect(apiGet('/trilhas')).resolves.toEqual({ total: 7 })
    expect(fetchFalso.mock.calls[0][0]).toContain('/api/v1/trilhas')
  })

  it('manda o access token quando existe', async () => {
    const fetchFalso = vi.fn().mockResolvedValue(respostaJson({}))
    vi.stubGlobal('fetch', fetchFalso)
    definirAccessToken('token-123')

    await apiGet('/usuarios/me')

    const headers = fetchFalso.mock.calls[0][1].headers as Headers
    expect(headers.get('Authorization')).toBe('Bearer token-123')
  })

  it('não manda token quando a chamada é pública', async () => {
    const fetchFalso = vi.fn().mockResolvedValue(respostaJson({}))
    vi.stubGlobal('fetch', fetchFalso)
    definirAccessToken('token-123')

    await apiPost('/auth/login', { email: 'a@b.c' }, { autenticar: false })

    const headers = fetchFalso.mock.calls[0][1].headers as Headers
    expect(headers.get('Authorization')).toBeNull()
  })

  it('aceita resposta 204 sem corpo', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })))

    await expect(apiPost('/auth/logout', {})).resolves.toBeUndefined()
  })
})

describe('leitura do erro', () => {
  it('lê o formato único da API', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        respostaJson(
          {
            erro: {
              code: 'email_em_uso',
              message: 'Já existe uma conta com esse e-mail',
              details: { campo: 'email' },
              request_id: 'abc-123',
            },
          },
          409,
        ),
      ),
    )

    const erro = await apiPost('/auth/register', {}).catch((e: unknown) => e)

    expect(erro).toBeInstanceOf(ApiError)
    const apiErro = erro as ApiError
    expect(apiErro.status).toBe(409)
    expect(apiErro.code).toBe('email_em_uso')
    expect(apiErro.message).toBe('Já existe uma conta com esse e-mail')
    expect(apiErro.details).toEqual({ campo: 'email' })
    expect(apiErro.requestId).toBe('abc-123')
  })

  it('ainda entende o `detail` do FastAPI, de resposta que não passou pelos handlers', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(respostaJson({ detail: 'Erro do proxy' }, 502)),
    )

    const erro = (await apiGet('/trilhas').catch((e: unknown) => e)) as ApiError

    expect(erro.message).toBe('Erro do proxy')
  })

  it('cai numa mensagem genérica quando o corpo não é JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('<html>502</html>', { status: 502 })),
    )

    const erro = (await apiGet('/trilhas').catch((e: unknown) => e)) as ApiError

    expect(erro.status).toBe(502)
    expect(erro.message).toContain('Algo deu errado')
  })

  it('avisa quando nem houve resposta', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const erro = (await apiGet('/trilhas').catch((e: unknown) => e)) as ApiError

    expect(erro.status).toBe(0)
    expect(erro.message).toContain('servidor')
  })
})

describe('renovação no 401', () => {
  it('renova a sessão e repete a chamada', async () => {
    const fetchFalso = vi
      .fn()
      .mockResolvedValueOnce(respostaJson({ erro: { code: 'nao_autenticado' } }, 401))
      .mockResolvedValueOnce(respostaJson({ username: 'ana' }))
    vi.stubGlobal('fetch', fetchFalso)
    configurarAutenticacao({ renovar: vi.fn().mockResolvedValue(true) })

    await expect(apiGet('/auth/eu')).resolves.toEqual({ username: 'ana' })
    expect(fetchFalso).toHaveBeenCalledTimes(2)
  })

  it('desiste quando a renovação falha', async () => {
    const fetchFalso = vi
      .fn()
      .mockResolvedValue(respostaJson({ erro: { code: 'nao_autenticado' } }, 401))
    vi.stubGlobal('fetch', fetchFalso)
    configurarAutenticacao({ renovar: vi.fn().mockResolvedValue(false) })

    await expect(apiGet('/auth/eu')).rejects.toBeInstanceOf(ApiError)
    expect(fetchFalso).toHaveBeenCalledTimes(1)
  })

  it('não tenta renovar quando a própria chamada é a renovação', async () => {
    // Senão a renovação esperaria por si mesma.
    const renovar = vi.fn().mockResolvedValue(true)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respostaJson({}, 401)))
    configurarAutenticacao({ renovar })

    await apiPost('/auth/refresh', {}, { renovar: false }).catch(() => undefined)

    expect(renovar).not.toHaveBeenCalled()
  })

  it('não renova em erro que não é 401', async () => {
    const renovar = vi.fn().mockResolvedValue(true)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respostaJson({}, 500)))
    configurarAutenticacao({ renovar })

    await apiGet('/trilhas').catch(() => undefined)

    expect(renovar).not.toHaveBeenCalled()
  })
})
