/**
 * Testes do formulário de login (tela 5).
 *
 * É a primeira tela com que o aluno esbarra e a que mais tem caminho de erro:
 * validação local, erro vindo da API e a escolha de continuar conectado.
 */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { LoginPage } from '@/pages/Auth/LoginPage'
import { useAuthStore } from '@/stores/useAuthStore'

const entrar = vi.fn()
const navegar = vi.fn()

vi.mock('react-router-dom', async () => {
  const real = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...real, useNavigate: () => navegar }
})

function montar() {
  return render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  entrar.mockReset().mockResolvedValue(undefined)
  navegar.mockReset()
  // O store de verdade, só com o login trocado: a tela não fala com a API.
  useAuthStore.setState({ entrar })
})

// O store vive no módulo, entre um teste e outro: volta ao começo.
afterEach(() => {
  useAuthStore.setState(useAuthStore.getInitialState(), true)
})

describe('validação', () => {
  it('cobra o e-mail quando o campo fica vazio', async () => {
    montar()

    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(await screen.findByText('Informe seu email.')).toBeInTheDocument()
    expect(entrar).not.toHaveBeenCalled()
  })

  it('liga a mensagem ao campo e foca o primeiro inválido', async () => {
    montar()

    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }))

    const email = screen.getByLabelText('Email')
    await waitFor(() => expect(email).toHaveFocus())
    // O leitor de tela lê a mensagem junto com o campo, não só quando ela aparece.
    expect(email).toHaveAccessibleDescription('Informe seu email.')
    expect(email).toHaveAttribute('aria-invalid', 'true')
  })

  it('recusa e-mail malformado', async () => {
    montar()

    await userEvent.type(screen.getByLabelText('Email'), 'nao-e-email')
    await userEvent.type(screen.getByLabelText('Senha'), 'senha-boa-2026')
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(await screen.findByText('Email inválido.')).toBeInTheDocument()
    expect(entrar).not.toHaveBeenCalled()
  })

  it('recusa senha curta sem chamar a API', async () => {
    montar()

    await userEvent.type(screen.getByLabelText('Email'), 'ana@ufrpe.br')
    await userEvent.type(screen.getByLabelText('Senha'), 'curta')
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(
      await screen.findByText('A senha precisa ter pelo menos 8 caracteres.'),
    ).toBeInTheDocument()
    expect(entrar).not.toHaveBeenCalled()
  })
})

describe('envio', () => {
  it('entra e vai para a home', async () => {
    montar()

    await userEvent.type(screen.getByLabelText('Email'), 'ana@ufrpe.br')
    await userEvent.type(screen.getByLabelText('Senha'), 'Trilha-Boa-2026')
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }))

    await waitFor(() =>
      expect(entrar).toHaveBeenCalledWith('ana@ufrpe.br', 'Trilha-Boa-2026', false),
    )
    expect(navegar).toHaveBeenCalledWith('/')
  })

  it('manda a escolha de manter-se conectado', async () => {
    montar()

    await userEvent.type(screen.getByLabelText('Email'), 'ana@ufrpe.br')
    await userEvent.type(screen.getByLabelText('Senha'), 'Trilha-Boa-2026')
    await userEvent.click(screen.getByLabelText('Manter-se conectado'))
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }))

    await waitFor(() =>
      expect(entrar).toHaveBeenCalledWith('ana@ufrpe.br', 'Trilha-Boa-2026', true),
    )
  })

  it('mostra a mensagem que a API devolveu', async () => {
    entrar.mockRejectedValue(new Error('E-mail ou senha incorretos'))
    montar()

    await userEvent.type(screen.getByLabelText('Email'), 'ana@ufrpe.br')
    await userEvent.type(screen.getByLabelText('Senha'), 'Trilha-Boa-2026')
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('E-mail ou senha incorretos')
    expect(navegar).not.toHaveBeenCalled()
  })
})

describe('acessibilidade', () => {
  it('liga rótulo e campo', () => {
    montar()

    expect(screen.getByLabelText('Email')).toHaveAttribute('type', 'email')
    expect(screen.getByLabelText('Senha')).toHaveAttribute('type', 'password')
  })

  it('marca o campo inválido para o leitor de tela', async () => {
    montar()

    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }))

    await waitFor(() =>
      expect(screen.getByLabelText('Email')).toHaveAttribute('aria-invalid', 'true'),
    )
  })

  it('oferece o caminho de recuperar a senha e o de criar conta', () => {
    montar()

    expect(screen.getByRole('link', { name: 'Esqueceu a senha?' })).toHaveAttribute(
      'href',
      '/esqueci-senha',
    )
    expect(screen.getByRole('link', { name: 'Criar conta' })).toHaveAttribute('href', '/cadastro')
  })
})
