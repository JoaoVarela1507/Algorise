/**
 * Desafio proposto (#25): o editor manda o código, a tela pergunta pela
 * execução até o veredito e mostra a tela de sucesso ou de falha. A API é um
 * `fetch` falso que responde pela URL.
 */
import { QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { criarQueryClient } from '@/lib/query'
import { DesafioPage } from '@/pages/Desafio/DesafioPage'

const TRILHA = {
  id: 1,
  slug: 'logica',
  nome: 'Lógica',
  disciplina: 'Algoritmos',
  total_modulos: 1,
  progresso: 1,
  modulos: [
    {
      id: 10,
      ordem: 1,
      titulo: 'Laços',
      status: 'concluido',
      concluido: true,
      bloqueado: false,
      atividades: [
        {
          id: 5,
          ordem: 1,
          tipo: 'multipla-escolha',
          enunciado: 'Pergunta',
          xp: 10,
          concluida: true,
        },
        { id: 6, ordem: 2, tipo: 'desafio-codigo', enunciado: 'Conte', xp: 40, concluida: false },
      ],
    },
  ],
}

const DESAFIO = {
  id: 6,
  enunciado: 'Faça uma contagem regressiva',
  dica: 'Use um laço',
  xp: 40,
  casos_publicos: [{ ordem: 1, entrada: '3\n', saida_esperada: '3\n2\n1\nFim!' }],
  total_casos: 3,
}

function execucao(extra: Record<string, unknown>) {
  return {
    id: 'abc',
    atividade_id: 6,
    status: 'concluida',
    aprovada: false,
    stdout: '',
    stderr: '',
    casos: [],
    criado_em: '2026-11-17T20:00:00Z',
    ...extra,
  }
}

let codigoEnviado: string | undefined

function api(resultado: Record<string, unknown>) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      const json = (corpo: unknown, status = 200) =>
        new Response(JSON.stringify(corpo), {
          status,
          headers: { 'Content-Type': 'application/json' },
        })
      if (url.endsWith('/trilhas/logica')) return json(TRILHA)
      if (url.endsWith('/desafios/6') && init?.method !== 'POST') return json(DESAFIO)
      if (url.endsWith('/desafios/6/execucoes')) {
        codigoEnviado = (JSON.parse(String(init?.body)) as { codigo: string }).codigo
        return json({ id: 'abc', status: 'na_fila' }, 202)
      }
      if (url.endsWith('/execucoes/abc')) return json(execucao(resultado))
      return json({}, 404)
    }),
  )
}

function montar() {
  return render(
    <QueryClientProvider client={criarQueryClient()}>
      <MemoryRouter initialEntries={['/trilhas/logica/desafio']}>
        <Routes>
          <Route path="/trilhas/:trilhaId/desafio" element={<DesafioPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

async function escreverEVerificar(codigo: string) {
  const editor = await screen.findByLabelText('Seu código em Python')
  fireEvent.change(editor, { target: { value: codigo } })
  await userEvent.click(screen.getByRole('button', { name: /Verificar/ }))
}

beforeEach(() => {
  codigoEnviado = undefined
  localStorage.clear()
})
afterEach(() => vi.unstubAllGlobals())

describe('desafio proposto', () => {
  it('mostra o enunciado, o exemplo e quantos casos são ocultos', async () => {
    api({})
    montar()

    expect(await screen.findByText('Faça uma contagem regressiva')).toBeInTheDocument()
    expect(screen.getByText(/3 casos de teste \(2 ocultos\)/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Verificar/ })).toBeDisabled()
  })

  it('aprovado: o polvo comemora com o XP', async () => {
    api({ aprovada: true, casos: [{ ordem: 1, publico: true, passou: true }] })
    montar()

    await escreverEVerificar('print("oi")')

    expect(await screen.findByText('Desafio concluído!')).toBeInTheDocument()
    expect(screen.getByText('+40 XP')).toBeInTheDocument()
    expect(codigoEnviado).toBe('print("oi")')
  })

  it('reprovado num caso público: mostra esperado e obtido, e volta ao editor', async () => {
    api({
      casos: [
        {
          ordem: 1,
          publico: true,
          passou: false,
          motivo: 'saida_diferente',
          entrada: '3\n',
          esperado: '3\n2\n1\nFim!',
          obtido: '3\n2\n1',
        },
      ],
    })
    montar()

    await escreverEVerificar('for i in range(3, 0, -1):\n    print(i)')

    expect(await screen.findByText('Tente novamente!')).toBeInTheDocument()
    expect(screen.getByText('Seu programa mostrou')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /Voltar para Desafio/ }))
    expect(screen.queryByText('Tente novamente!')).not.toBeInTheDocument()
    // O código continua no editor para o aluno corrigir.
    expect(screen.getByLabelText('Seu código em Python')).toHaveValue(
      'for i in range(3, 0, -1):\n    print(i)',
    )
  })

  it('erro de execução mostra a última linha do traceback', async () => {
    api({
      stderr: 'Traceback (most recent call last):\n  File "<string>", line 1\nValueError: ruim',
      casos: [{ ordem: 2, publico: false, passou: false, motivo: 'erro_de_execucao' }],
    })
    montar()

    await escreverEVerificar('int("x")')

    expect(await screen.findByText('ValueError: ruim')).toBeInTheDocument()
    expect(screen.getByText(/caso de teste oculto/)).toBeInTheDocument()
  })
})
