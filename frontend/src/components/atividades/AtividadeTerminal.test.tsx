/**
 * Testes da atividade de terminal.
 *
 * O Xterm desenha em `<canvas>`, que o jsdom não implementa — então o que se
 * exercita aqui é a entrada alternativa, que é justamente o caminho de quem usa
 * teclado e leitor de tela. O roteiro tem os testes dele em
 * `lib/terminal/roteiro.test.ts`, e o terminal desenhado de verdade é coberto
 * pelo E2E.
 */
import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AtividadeTerminal } from '@/components/atividades/AtividadeTerminal'
import { criarQueryClient } from '@/lib/query'
import { ATIVIDADES } from '@/lib/terminal/roteiro'

const versao = ATIVIDADES['python --version']
const avancar = vi.fn()

/** Resposta da API de submissão (`POST /atividades/{id}/submissoes`). */
function correcao(correta: boolean, xpGanho = 0) {
  return new Response(
    JSON.stringify({
      correta,
      em_analise: false,
      feedback: correta ? 'Comando correto!' : 'Não é esse o comando.',
      tentativa: 1,
      xp_ganho: xpGanho,
      xp_total: xpGanho,
    }),
    { status: 201, headers: { 'Content-Type': 'application/json' } },
  )
}

/** Por padrão a API confirma o que o roteiro local achou. */
function apiQueConfereOComando() {
  return vi.fn(async (_url: string, init?: RequestInit) => {
    const corpo = JSON.parse(String(init?.body ?? '{}')) as { conteudo?: string }
    const certo = (corpo.conteudo ?? '').trim().toLowerCase() === 'python --version'
    return correcao(certo, certo ? 10 : 0)
  })
}

function montar(props: Partial<Parameters<typeof AtividadeTerminal>[0]> = {}) {
  const queryClient = criarQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <AtividadeTerminal
        atividadeId={42}
        enunciado="Verifique a versão do Python"
        dica="Está no vídeo, depois da instalação"
        atividade={versao}
        numero={2}
        total={3}
        aoAvancar={avancar}
        {...props}
      />
    </QueryClientProvider>,
  )
}

/** Digita no campo alternativo e envia. */
async function digitar(comando: string) {
  const campo = screen.getByLabelText('Digite o comando da atividade')
  await userEvent.type(campo, `${comando}{Enter}`)
}

beforeEach(() => {
  avancar.mockReset()
  vi.stubGlobal('fetch', apiQueConfereOComando())
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('avançar', () => {
  it('começa bloqueado', () => {
    montar()

    expect(screen.getByRole('button', { name: 'Avançar' })).toBeDisabled()
  })

  it('libera depois do comando certo', async () => {
    montar()

    await digitar('python --version')

    await waitFor(() => expect(screen.getByRole('button', { name: 'Avançar' })).toBeEnabled())
    expect(screen.getByText('Comando correto!')).toBeInTheDocument()
  })

  it('continua bloqueado depois de um comando errado', async () => {
    montar()

    await digitar('python ---version')

    await waitFor(() => expect(screen.getByText(/Tentativas: 1/)).toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Avançar' })).toBeDisabled()
  })

  it('conta as tentativas erradas', async () => {
    montar()

    await digitar('ls')
    await digitar('python ---version')

    await waitFor(() => expect(screen.getByText(/Tentativas: 2/)).toBeInTheDocument())
  })

  it('o erro não impede o acerto depois', async () => {
    montar()

    await digitar('python ---version')
    await digitar('python --version')

    await waitFor(() => expect(screen.getByRole('button', { name: 'Avançar' })).toBeEnabled())
  })

  it('chama quem passou o `aoAvancar`', async () => {
    montar()

    await digitar('python --version')
    await waitFor(() => expect(screen.getByRole('button', { name: 'Avançar' })).toBeEnabled())
    await userEvent.click(screen.getByRole('button', { name: 'Avançar' }))

    expect(avancar).toHaveBeenCalledOnce()
  })

  it('quem decide é o servidor, não o roteiro local', async () => {
    // O comando está certo para o roteiro, mas a API diz que não: o que vale é
    // a API, senão bastaria mexer no JavaScript da página para "acertar".
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(correcao(false)))
    montar()

    await digitar('python --version')

    await waitFor(() => expect(screen.getByText(/Tentativas: 1/)).toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Avançar' })).toBeDisabled()
  })

  it('API fora não conta tentativa errada', async () => {
    // Sem resposta não dá para afirmar que o aluno errou.
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    montar()

    await digitar('python --version')

    await waitFor(() =>
      expect(screen.getByText('Digite o comando no terminal para continuar.')).toBeInTheDocument(),
    )
    expect(screen.queryByText(/Tentativas:/)).not.toBeInTheDocument()
  })

  it('atividade já concluída abre liberada', () => {
    montar({ concluida: true })

    expect(screen.getByRole('button', { name: 'Avançar' })).toBeEnabled()
  })
})

describe('enunciado e dica', () => {
  it('mostra o enunciado', () => {
    montar()

    expect(screen.getByRole('heading', { name: 'Verifique a versão do Python' })).toBeVisible()
  })

  it('a dica fica escondida até o aluno pedir', async () => {
    montar()

    expect(screen.queryByText(/Está no vídeo/)).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /Ver dica/ }))

    expect(screen.getByText(/Está no vídeo/)).toBeVisible()
  })

  it('atividade sem dica não mostra o botão', () => {
    montar({ dica: null })

    expect(screen.queryByRole('button', { name: /dica/ })).not.toBeInTheDocument()
  })
})

describe('acessibilidade', () => {
  it('o progresso é anunciável', () => {
    montar()

    const barra = screen.getByRole('progressbar', { name: 'Atividade 2 de 3' })
    expect(barra).toHaveAttribute('aria-valuenow', '2')
    expect(barra).toHaveAttribute('aria-valuemax', '3')
  })

  it('a saída do terminal existe em texto para leitor de tela', async () => {
    montar()

    await digitar('python --version')

    const log = screen.getByRole('log', { name: 'Saída do terminal' })
    await waitFor(() => expect(log).toHaveTextContent('Python 3.14.0'))
  })

  it('explica por que o Avançar não responde', () => {
    montar()

    expect(
      screen.getByText('O botão Avançar libera depois que você acertar o comando.'),
    ).toBeInTheDocument()
  })

  it('dá para completar a atividade só pelo teclado', async () => {
    montar()

    // Tab até o campo e digita, sem clicar em nada.
    await userEvent.tab()
    await userEvent.tab()
    await userEvent.keyboard('python --version{Enter}')

    await waitFor(() => expect(screen.getByRole('button', { name: 'Avançar' })).toBeEnabled())
  })
})

describe('cronômetro', () => {
  it('mostra o tempo sugerido', () => {
    montar({ tempoSugeridoSegundos: 90 })

    expect(screen.getByText('1:30 sugeridos')).toBeInTheDocument()
  })

  it('não aparece quando a atividade não sugere tempo', () => {
    montar({ tempoSugeridoSegundos: null })

    expect(screen.queryByText(/sugeridos/)).not.toBeInTheDocument()
  })
})
