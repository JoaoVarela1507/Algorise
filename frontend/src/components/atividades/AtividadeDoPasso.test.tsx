/**
 * Testes das atividades que não são de terminal: múltipla escolha, ordenação,
 * lacunas, resposta aberta e desafio. Em todas, quem diz se acertou é a API —
 * aqui ela é um `fetch` falso que confere o que a tela mandou.
 */
import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AtividadeDoPasso } from '@/components/atividades/AtividadeDoPasso'
import { criarQueryClient } from '@/lib/query'
import type { AtividadeApi } from '@/services/atividades'

const avancar = vi.fn()
let enviado: string | undefined

function resposta(corpo: Record<string, unknown>) {
  return new Response(
    JSON.stringify({ tentativa: 1, xp_ganho: 0, xp_total: 0, em_analise: false, ...corpo }),
    { status: 201, headers: { 'Content-Type': 'application/json' } },
  )
}

/** A API acerta quando recebe exatamente `gabarito`. */
function apiComGabarito(gabarito: string, feedbackDoErro = 'Não é essa.') {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (_url: string, init?: RequestInit) => {
      enviado = (JSON.parse(String(init?.body ?? '{}')) as { conteudo?: string }).conteudo
      const correta = enviado === gabarito
      return resposta({ correta, feedback: correta ? 'Isso mesmo!' : feedbackDoErro })
    }),
  )
}

function atividade(extra: Partial<AtividadeApi>): AtividadeApi {
  return {
    id: 7,
    ordem: 1,
    tipo: 'multipla-escolha',
    enunciado: 'Pergunta',
    xp: 10,
    concluida: false,
    ...extra,
  } as AtividadeApi
}

function montar(dados: AtividadeApi) {
  return render(
    <QueryClientProvider client={criarQueryClient()}>
      <AtividadeDoPasso atividade={dados} roteiro={null} numero={1} total={2} aoAvancar={avancar} />
    </QueryClientProvider>,
  )
}

const avancarBotao = () => screen.getByRole('button', { name: 'Avançar' })

beforeEach(() => {
  avancar.mockReset()
  enviado = undefined
})

afterEach(() => vi.unstubAllGlobals())

describe('múltipla escolha', () => {
  const dados = atividade({ opcoes: ['int', 'float', 'str'] })

  it('só confere depois de escolher', () => {
    apiComGabarito('float')
    montar(dados)

    expect(screen.getByRole('button', { name: 'Conferir' })).toBeDisabled()
    expect(avancarBotao()).toBeDisabled()
  })

  it('libera o Avançar com a alternativa certa', async () => {
    apiComGabarito('float')
    montar(dados)

    await userEvent.click(screen.getByLabelText('float'))
    await userEvent.click(screen.getByRole('button', { name: 'Conferir' }))

    await waitFor(() => expect(avancarBotao()).toBeEnabled())
    expect(enviado).toBe('float')
    expect(screen.getByText('Isso mesmo!')).toBeInTheDocument()
  })

  it('a errada conta tentativa e mostra o que o servidor disse', async () => {
    apiComGabarito('float', 'Releia o enunciado.')
    montar(dados)

    await userEvent.click(screen.getByLabelText('int'))
    await userEvent.click(screen.getByRole('button', { name: 'Conferir' }))

    await waitFor(() => expect(screen.getByText(/Tentativas: 1/)).toBeInTheDocument())
    expect(screen.getByText('Releia o enunciado.')).toBeInTheDocument()
    expect(avancarBotao()).toBeDisabled()
  })

  it('a dica abre sozinha depois de dois erros', async () => {
    apiComGabarito('float')
    montar(atividade({ opcoes: ['int', 'float'], dica: 'Tem vírgula' }))

    expect(screen.queryByText('Tem vírgula')).not.toBeInTheDocument()
    await userEvent.click(screen.getByLabelText('int'))
    await userEvent.click(screen.getByRole('button', { name: 'Conferir' }))
    await waitFor(() => expect(screen.getByText(/Tentativas: 1/)).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button', { name: 'Conferir' }))

    await waitFor(() => expect(screen.getByText('Tem vírgula')).toBeVisible())
  })

  it('atividade já feita abre liberada', () => {
    apiComGabarito('float')
    montar(atividade({ opcoes: ['int', 'float'], concluida: true }))

    expect(avancarBotao()).toBeEnabled()
  })
})

describe('ordenação', () => {
  it('manda as linhas na ordem em que o aluno deixou', async () => {
    const certo = JSON.stringify(['a = 1', 'print(a)'])
    apiComGabarito(certo)
    montar(atividade({ tipo: 'ordenacao', opcoes: ['print(a)', 'a = 1'] }))

    await userEvent.click(screen.getByRole('button', { name: 'Descer a linha 1' }))
    await userEvent.click(screen.getByRole('button', { name: 'Conferir' }))

    await waitFor(() => expect(avancarBotao()).toBeEnabled())
    expect(enviado).toBe(certo)
  })

  it('a primeira linha não sobe e a última não desce', () => {
    apiComGabarito('[]')
    montar(atividade({ tipo: 'ordenacao', opcoes: ['x', 'y'] }))

    expect(screen.getByRole('button', { name: 'Subir a linha 1' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Descer a linha 2' })).toBeDisabled()
  })
})

describe('lacunas', () => {
  const dados = atividade({
    tipo: 'preencher-lacuna',
    codigo: '___ dobro(n):\n    ___ n * 2',
    opcoes: ['def', 'return', 'print'],
  })

  it('um campo por buraco, e só confere com todos preenchidos', async () => {
    apiComGabarito('')
    montar(dados)

    expect(screen.getByLabelText('Lacuna 1 de 2')).toBeInTheDocument()
    expect(screen.getByLabelText('Lacuna 2 de 2')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Conferir' })).toBeDisabled()
  })

  it('o banco de palavras preenche os buracos em ordem', async () => {
    const certo = JSON.stringify(['def', 'return'])
    apiComGabarito(certo)
    montar(dados)

    await userEvent.click(screen.getByRole('button', { name: 'def' }))
    await userEvent.click(screen.getByRole('button', { name: 'return' }))
    await userEvent.click(screen.getByRole('button', { name: 'Conferir' }))

    await waitFor(() => expect(avancarBotao()).toBeEnabled())
    expect(enviado).toBe(certo)
  })

  it('dá para digitar no buraco', async () => {
    const certo = JSON.stringify(['def', 'return'])
    apiComGabarito(certo)
    montar(dados)

    await userEvent.type(screen.getByLabelText('Lacuna 1 de 2'), 'def')
    await userEvent.type(screen.getByLabelText('Lacuna 2 de 2'), 'return')
    await userEvent.click(screen.getByRole('button', { name: 'Conferir' }))

    await waitFor(() => expect(avancarBotao()).toBeEnabled())
  })
})

describe('resposta aberta', () => {
  it('pede o mínimo de caracteres e libera quando fica em análise', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        resposta({ correta: false, em_analise: true, feedback: 'Resposta recebida.' }),
      ),
    )
    montar(atividade({ tipo: 'resposta-aberta' }))

    const campo = screen.getByLabelText('Sua resposta')
    await userEvent.type(campo, 'curta')
    expect(screen.getByRole('button', { name: 'Enviar' })).toBeDisabled()

    await userEvent.type(campo, ' mas agora já passou do mínimo')
    await userEvent.click(screen.getByRole('button', { name: 'Enviar' }))

    await waitFor(() => expect(avancarBotao()).toBeEnabled())
    expect(screen.getByText('Resposta recebida.')).toBeInTheDocument()
  })
})

describe('desafio de código', () => {
  it('ainda sem correção, não trava o passo', async () => {
    apiComGabarito('')
    montar(atividade({ tipo: 'desafio-codigo' }))

    expect(avancarBotao()).toBeEnabled()
    await userEvent.click(avancarBotao())
    expect(avancar).toHaveBeenCalledOnce()
  })
})
