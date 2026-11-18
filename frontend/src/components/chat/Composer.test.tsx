import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Composer } from './Composer'
import { MensagemChat } from './MensagemChat'

const fetchFalso = vi.fn()

afterEach(() => {
  vi.unstubAllGlobals()
  fetchFalso.mockReset()
})

function resposta(corpo: unknown, status = 201) {
  return new Response(status === 204 ? null : JSON.stringify(corpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function montar(onEnviar = vi.fn()) {
  vi.stubGlobal('fetch', fetchFalso)
  render(<Composer onEnviar={onEnviar} ocupado={false} modo="medio" onModoChange={() => {}} />)
  return onEnviar
}

const campoArquivo = () => document.querySelector('input[type="file"]') as HTMLInputElement

describe('anexos no Composer', () => {
  it('sobe o arquivo, mostra o chip e manda o anexo junto da mensagem', async () => {
    const anexo = { id: 5, nome: 'laco.py', tipo: 'texto', tamanho: 12 }
    fetchFalso.mockResolvedValue(resposta(anexo))
    const onEnviar = montar()

    await userEvent.upload(campoArquivo(), new File(['print(1)'], 'laco.py'))
    expect(await screen.findByText('laco.py')).toBeInTheDocument()
    await waitFor(() => expect(screen.queryByText(/enviando/)).toBeNull())

    await userEvent.type(screen.getByLabelText('Mensagem'), 'Explica esse código')
    await userEvent.click(screen.getByRole('button', { name: 'Enviar mensagem' }))

    expect(onEnviar).toHaveBeenCalledWith('Explica esse código', [anexo])
  })

  it('remover o chip apaga o anexo no servidor', async () => {
    fetchFalso
      .mockResolvedValueOnce(resposta({ id: 8, nome: 'a.pdf', tipo: 'pdf', tamanho: 3 }))
      .mockResolvedValueOnce(resposta(null, 204))
    montar()

    await userEvent.upload(campoArquivo(), new File(['%PDF-'], 'a.pdf'))
    await waitFor(() => expect(screen.queryByText(/enviando/)).toBeNull())
    await userEvent.click(screen.getByRole('button', { name: /Remover anexo a.pdf/ }))

    await waitFor(() => expect(screen.queryByText('a.pdf')).toBeNull())
    const [url, init] = fetchFalso.mock.calls[1] as [string, RequestInit]
    expect(url).toContain('/chat/anexos/8')
    expect(init.method).toBe('DELETE')
  })

  it('recusa tipo não aceito sem chamar a API e explica o motivo', async () => {
    montar()
    // `applyAccept: false`: o teste quer ver a validação do código, não o filtro do input.
    await userEvent.upload(campoArquivo(), new File(['MZ'], 'virus.exe'), { applyAccept: false })

    expect(await screen.findByRole('alert')).toHaveTextContent(/Tipo de arquivo não aceito/)
    expect(fetchFalso).not.toHaveBeenCalled()
  })

  it('mostra a mensagem da API quando o upload falha', async () => {
    fetchFalso.mockResolvedValue(
      resposta({ erro: { code: 'anexo_invalido', message: 'Não consegui ler esse PDF.' } }, 415),
    )
    montar()

    await userEvent.upload(campoArquivo(), new File(['x'], 'ruim.pdf'))

    expect(await screen.findByRole('alert')).toHaveTextContent('Não consegui ler esse PDF.')
    await waitFor(() => expect(screen.queryByText('ruim.pdf')).toBeNull())
  })
})

describe('anexo na mensagem enviada', () => {
  it('mostra o chip com o nome do arquivo', () => {
    render(
      <MensagemChat
        mensagem={{
          id: '1',
          autor: 'usuario',
          conteudo: 'Olha isso',
          criadaEm: 0,
          anexos: [{ id: 1, nome: 'notas.pdf', tipo: 'pdf', tamanho: 2048 }],
        }}
      />,
    )
    expect(screen.getByRole('button', { name: /notas\.pdf/ })).toBeInTheDocument()
    expect(screen.getByText('2 KB')).toBeInTheDocument()
  })
})
