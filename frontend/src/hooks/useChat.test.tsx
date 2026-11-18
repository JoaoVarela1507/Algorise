/**
 * Histórico, grupos e anexos do chat pela API (#23, #33): as rotas certas, o
 * corpo certo e a invalidação do cache depois de cada ação.
 */
import { QueryClientProvider, type QueryClient } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  atualizarDepoisDaResposta,
  useApagarConversa,
  useConversas,
  useCriarGrupo,
  useEditarGrupo,
  useGrupos,
  useMensagens,
  useRenomearConversa,
} from '@/hooks/useChat'
import { chaves, criarQueryClient } from '@/lib/query'
import { apagarHistoricoChat, enviarAnexo, validarAnexo } from '@/services/chat'

let queryClient: QueryClient
const fetchFalso = vi.fn()

beforeEach(() => {
  queryClient = criarQueryClient()
  fetchFalso.mockReset()
  vi.stubGlobal('fetch', fetchFalso)
})

afterEach(() => {
  queryClient.clear()
  vi.unstubAllGlobals()
})

function Provider({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

function json(corpo: unknown, status = 200) {
  return new Response(status === 204 ? null : JSON.stringify(corpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function pagina<T>(itens: T[], numero = 1, totalPaginas = 1) {
  return {
    itens,
    pagina: numero,
    tamanho_pagina: 50,
    total: itens.length,
    total_paginas: totalPaginas,
  }
}

const conversa = (id: number, extra = {}) => ({
  id,
  titulo: `Conversa ${id}`,
  arquivada: false,
  grupo_id: null,
  criado_em: '2026-11-17T10:00:00Z',
  atualizado_em: '2026-11-17T10:00:00Z',
  ...extra,
})

function chamadas() {
  return fetchFalso.mock.calls.map(([url, init]) => ({
    url: String(url),
    metodo: (init as RequestInit | undefined)?.method ?? 'GET',
    corpo: (init as RequestInit | undefined)?.body,
  }))
}

describe('leitura', () => {
  it('lista conversas com a busca no servidor', async () => {
    fetchFalso.mockResolvedValue(json(pagina([conversa(1)])))
    const { result } = renderHook(() => useConversas('laço'), { wrapper: Provider })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(chamadas()[0].url).toContain('/api/v1/chat/conversas?')
    expect(chamadas()[0].url).toContain('busca=la%C3%A7o')
    expect(result.current.data?.pages[0].itens[0].id).toBe(1)
  })

  it('carrega a página seguinte da lista', async () => {
    fetchFalso
      .mockResolvedValueOnce(json(pagina([conversa(1)], 1, 2)))
      .mockResolvedValueOnce(json(pagina([conversa(2)], 2, 2)))
    const { result } = renderHook(() => useConversas(), { wrapper: Provider })
    await waitFor(() => expect(result.current.hasNextPage).toBe(true))

    await act(() => result.current.fetchNextPage())

    expect(chamadas()[1].url).toContain('pagina=2')
    await waitFor(() => expect(result.current.hasNextPage).toBe(false))
  })

  it('junta todas as páginas de mensagens da conversa', async () => {
    const mensagem = (id: number) => ({
      id,
      papel: 'usuario',
      conteudo: `m${id}`,
      incompleta: false,
      criado_em: '2026-11-17T10:00:00Z',
      anexos: [],
    })
    fetchFalso
      .mockResolvedValueOnce(json(pagina([mensagem(1)], 1, 2)))
      .mockResolvedValueOnce(json(pagina([mensagem(2)], 2, 2)))
    const { result } = renderHook(() => useMensagens(7), { wrapper: Provider })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.map((m) => m.id)).toEqual([1, 2])
    expect(chamadas()[0].url).toContain('/chat/conversas/7/mensagens?pagina=1')
  })

  it('não busca mensagens sem conversa aberta', () => {
    renderHook(() => useMensagens(null), { wrapper: Provider })
    expect(fetchFalso).not.toHaveBeenCalled()
  })

  it('lista os grupos', async () => {
    fetchFalso.mockResolvedValue(json([{ id: 1, nome: 'Redes', conversas: [], criado_em: 'x' }]))
    const { result } = renderHook(() => useGrupos(), { wrapper: Provider })
    await waitFor(() => expect(result.current.data?.[0].nome).toBe('Redes'))
    expect(chamadas()[0].url).toContain('/api/v1/chat/grupos')
  })
})

describe('ações', () => {
  it('renomear usa PATCH e invalida o histórico', async () => {
    fetchFalso.mockResolvedValue(json(conversa(3, { titulo: 'Novo' })))
    const invalidar = vi.spyOn(queryClient, 'invalidateQueries')
    const { result } = renderHook(() => useRenomearConversa(), { wrapper: Provider })

    await act(() => result.current.mutateAsync({ id: 3, titulo: 'Novo' }))

    expect(chamadas()[0]).toMatchObject({ metodo: 'PATCH' })
    expect(chamadas()[0].url).toContain('/chat/conversas/3')
    expect(JSON.parse(chamadas()[0].corpo as string)).toEqual({ titulo: 'Novo' })
    expect(invalidar).toHaveBeenCalledWith({ queryKey: chaves.chat.todas })
  })

  it('apagar usa DELETE, descarta as mensagens em cache e invalida', async () => {
    fetchFalso.mockResolvedValue(json(null, 204))
    queryClient.setQueryData(chaves.chat.mensagens(4), [])
    const { result } = renderHook(() => useApagarConversa(), { wrapper: Provider })

    await act(() => result.current.mutateAsync(4))

    expect(chamadas()[0]).toMatchObject({ metodo: 'DELETE' })
    expect(queryClient.getQueryData(chaves.chat.mensagens(4))).toBeUndefined()
  })

  it('cria grupo com as conversas escolhidas', async () => {
    fetchFalso.mockResolvedValue(json({ id: 1, nome: 'Redes', conversas: [], criado_em: 'x' }, 201))
    const { result } = renderHook(() => useCriarGrupo(), { wrapper: Provider })

    await act(() => result.current.mutateAsync({ nome: 'Redes', conversaIds: [1, 2] }))

    expect(chamadas()[0]).toMatchObject({ metodo: 'POST' })
    expect(JSON.parse(chamadas()[0].corpo as string)).toEqual({
      nome: 'Redes',
      conversa_ids: [1, 2],
    })
  })

  it('edita o grupo mandando a lista inteira de conversas', async () => {
    fetchFalso.mockResolvedValue(json({ id: 1, nome: 'Redes 2', conversas: [], criado_em: 'x' }))
    const { result } = renderHook(() => useEditarGrupo(), { wrapper: Provider })

    await act(() => result.current.mutateAsync({ id: 1, nome: 'Redes 2', conversaIds: [2] }))

    expect(chamadas()[0]).toMatchObject({ metodo: 'PATCH' })
    expect(chamadas()[0].url).toContain('/chat/grupos/1')
    expect(JSON.parse(chamadas()[0].corpo as string)).toEqual({
      nome: 'Redes 2',
      conversa_ids: [2],
    })
  })

  it('depois da resposta do tutor, recarrega a lista e as mensagens da conversa', async () => {
    fetchFalso.mockImplementation(async (url: string) =>
      url.includes('/mensagens') ? json(pagina([])) : json(pagina([conversa(9)])),
    )
    queryClient.setQueryData(chaves.chat.conversas(''), { pages: [], pageParams: [] })
    const { result } = renderHook(() => useConversas(), { wrapper: Provider })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    fetchFalso.mockClear()

    await atualizarDepoisDaResposta(queryClient, 9)

    const urls = chamadas().map((c) => c.url)
    expect(urls.some((u) => u.includes('/chat/conversas?'))).toBe(true)
    expect(urls.some((u) => u.includes('/chat/conversas/9/mensagens'))).toBe(true)
  })

  it('apagar o histórico apaga todas as conversas, página por página', async () => {
    fetchFalso
      .mockResolvedValueOnce(json(pagina([conversa(1), conversa(2)])))
      .mockResolvedValueOnce(json(null, 204))
      .mockResolvedValueOnce(json(null, 204))
      .mockResolvedValueOnce(json(pagina([])))

    await apagarHistoricoChat()

    expect(
      chamadas()
        .filter((c) => c.metodo === 'DELETE')
        .map((c) => c.url),
    ).toEqual([
      expect.stringContaining('/chat/conversas/1'),
      expect.stringContaining('/chat/conversas/2'),
    ])
  })
})

describe('anexos', () => {
  it('aceita texto, código, PDF e imagem', () => {
    for (const nome of ['a.py', 'notas.TXT', 'prova.pdf', 'foto.jpeg', 'x.webp']) {
      expect(validarAnexo(new File(['x'], nome))).toBeNull()
    }
  })

  it('recusa tipo desconhecido, arquivo grande e vazio com mensagem amigável', () => {
    expect(validarAnexo(new File(['x'], 'app.exe'))).toMatch(/Tipo de arquivo não aceito/)
    const grande = new File([new Uint8Array(2 * 1024 * 1024 + 1)], 'grande.pdf')
    expect(validarAnexo(grande)).toMatch(/até 2 MB/)
    expect(validarAnexo(new File([], 'vazio.txt'))).toMatch(/vazio/)
  })

  it('envia o arquivo em multipart para POST /chat/anexos', async () => {
    fetchFalso.mockResolvedValue(json({ id: 5, nome: 'a.py', tipo: 'texto', tamanho: 1 }, 201))

    const anexo = await enviarAnexo(new File(['x'], 'a.py'))

    expect(anexo.id).toBe(5)
    const [url, init] = fetchFalso.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/api/v1/chat/anexos')
    expect(init.method).toBe('POST')
    expect(init.body).toBeInstanceOf(FormData)
    expect((init.body as FormData).get('arquivo')).toBeInstanceOf(File)
    // Sem Content-Type à mão, para o navegador pôr o boundary.
    expect(new Headers(init.headers).has('Content-Type')).toBe(false)
  })
})
