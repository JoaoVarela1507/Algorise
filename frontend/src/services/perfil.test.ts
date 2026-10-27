/**
 * Testes das chamadas do perfil (#27) em `services/auth.ts`.
 *
 * O que pode dar errado aqui é silencioso: a foto com caminho relativo apontando
 * para o servidor do frontend, ou o envio da foto com `Content-Type` de JSON,
 * que o backend recusa sem dizer por quê.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { API_URL, definirAccessToken } from '@/services/api'
import {
  enviarAvatar,
  removerAvatar,
  salvarPreferencias,
  trocarModoTrilha,
  urlDoAvatar,
} from '@/services/auth'

const PERFIL = {
  id: 7,
  email: 'ana@ufrpe.br',
  username: 'ana',
  nome_exibicao: 'Ana Lima',
  avatar_url: '/media/avatares/7-abc.webp',
  tem_senha: true,
  xp_total: 120,
  streak_dias: 2,
  nivel_experiencia: 'baixo',
  tipo_trilha: 'livre',
  instituicao: null,
  curso: null,
  periodo: null,
  preferencias: { tamanho_fonte: 'alta', alto_contraste: true, reduzir_animacoes: false },
}

function respostaJson(corpo: unknown) {
  return new Response(JSON.stringify(corpo), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

function simularApi(corpo: unknown = PERFIL) {
  const fetchFalso = vi.fn().mockResolvedValue(respostaJson(corpo))
  vi.stubGlobal('fetch', fetchFalso)
  return fetchFalso
}

beforeEach(() => definirAccessToken('token'))
afterEach(() => vi.unstubAllGlobals())

describe('urlDoAvatar', () => {
  it('completa a foto enviada com o endereço da API', () => {
    expect(urlDoAvatar('/media/avatares/x.webp')).toBe(`${API_URL}/media/avatares/x.webp`)
  })

  it('deixa como está a foto do GitHub ou do Google', () => {
    const externa = 'https://avatars.githubusercontent.com/u/1'
    expect(urlDoAvatar(externa)).toBe(externa)
  })

  it('sem foto, sem URL', () => {
    expect(urlDoAvatar(null)).toBeUndefined()
  })
})

describe('trocarModoTrilha', () => {
  it('usa a rota própria e traduz o perfil de volta', async () => {
    const fetchFalso = simularApi()

    const usuario = await trocarModoTrilha('livre')

    const [url, init] = fetchFalso.mock.calls[0]
    expect(url).toContain('/api/v1/usuarios/me/trilha')
    expect(init.method).toBe('PATCH')
    expect(JSON.parse(init.body as string)).toEqual({ tipo_trilha: 'livre' })
    expect(usuario.tipoTrilha).toBe('livre')
    expect(usuario.avatarUrl).toBe(`${API_URL}/media/avatares/7-abc.webp`)
    expect(usuario.preferencias).toEqual({
      tamanhoFonte: 'alta',
      altoContraste: true,
      reduzirAnimacoes: false,
    })
  })
})

describe('salvarPreferencias', () => {
  it('manda só o que mudou, no formato da API', async () => {
    const fetchFalso = simularApi(PERFIL.preferencias)

    const preferencias = await salvarPreferencias({ altoContraste: true })

    const [url, init] = fetchFalso.mock.calls[0]
    expect(url).toContain('/api/v1/usuarios/me/preferencias')
    // `undefined` some no JSON: o PATCH parcial do backend não mexe no resto.
    expect(JSON.parse(init.body as string)).toEqual({ alto_contraste: true })
    expect(preferencias.tamanhoFonte).toBe('alta')
  })
})

describe('foto do perfil', () => {
  it('envia o arquivo como multipart, sem Content-Type de JSON', async () => {
    const fetchFalso = simularApi()
    const arquivo = new File(['png'], 'foto.png', { type: 'image/png' })

    await enviarAvatar(arquivo)

    const [url, init] = fetchFalso.mock.calls[0]
    expect(url).toContain('/api/v1/usuarios/me/avatar')
    expect(init.method).toBe('PUT')
    expect((init.body as FormData).get('arquivo')).toBeInstanceOf(File)
    expect((init.headers as Headers).has('Content-Type')).toBe(false)
  })

  it('remove com DELETE e volta sem foto', async () => {
    const fetchFalso = simularApi({ ...PERFIL, avatar_url: null })

    const usuario = await removerAvatar()

    expect(fetchFalso.mock.calls[0][1].method).toBe('DELETE')
    expect(usuario.avatarUrl).toBeUndefined()
  })
})
