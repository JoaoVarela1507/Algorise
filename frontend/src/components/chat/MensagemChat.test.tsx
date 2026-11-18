import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/services/api'
import { mensagemDeErro, podeTentarDeNovo } from './erros'
import { MensagemChat } from './MensagemChat'

const base = { id: '1', autor: 'assistente' as const, criadaEm: 0 }

describe('mensagemDeErro', () => {
  it.each([
    ['rate_limit', 429, /muitas mensagens/],
    ['ia_indisponivel', 503, /fora do ar/],
    ['chat_ocupado', 409, /ainda está respondendo/],
    ['conversa_nao_encontrada', 404, /novo bate-papo/],
    ['erro_interno', 500, /do nosso lado/],
  ])('traduz o código %s', (code, status, esperado) => {
    expect(mensagemDeErro(new ApiError(status, 'x', code))).toMatch(esperado)
  })

  it('trata queda de rede, timeout e erro desconhecido', () => {
    expect(mensagemDeErro(new ApiError(0, 'x'))).toMatch(/Sem conexão/)
    expect(mensagemDeErro(new ApiError(504, 'x'))).toMatch(/demorou demais/)
    expect(mensagemDeErro(new Error('boom'))).toMatch(/Não consegui responder/)
  })

  it('só desiste de repetir quando a conversa sumiu', () => {
    expect(podeTentarDeNovo(new ApiError(404, 'x', 'conversa_nao_encontrada'))).toBe(false)
    expect(podeTentarDeNovo(new ApiError(503, 'x', 'ia_indisponivel'))).toBe(true)
  })
})

describe('MensagemChat', () => {
  it('mostra o erro com "Tentar de novo" que dispara o reenvio', async () => {
    const aoTentarDeNovo = vi.fn()
    render(
      <MensagemChat
        mensagem={{ ...base, conteudo: 'O tutor está fora do ar.', erro: true }}
        aoTentarDeNovo={aoTentarDeNovo}
      />,
    )
    expect(screen.getByText('Erro')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /Tentar de novo/ }))
    expect(aoTentarDeNovo).toHaveBeenCalledOnce()
  })

  it('marca a resposta interrompida e mantém o texto parcial', () => {
    render(<MensagemChat mensagem={{ ...base, conteudo: 'Recursão é quando', incompleta: true }} />)
    expect(screen.getByText('Recursão é quando')).toBeInTheDocument()
    expect(screen.getByText(/Resposta interrompida/)).toBeInTheDocument()
  })

  it('não mostra marca nem botão numa resposta normal', () => {
    render(<MensagemChat mensagem={{ ...base, conteudo: 'Tudo certo' }} />)
    expect(screen.queryByText(/interrompida/)).toBeNull()
    expect(screen.queryByRole('button', { name: /Tentar de novo/ })).toBeNull()
  })
})
