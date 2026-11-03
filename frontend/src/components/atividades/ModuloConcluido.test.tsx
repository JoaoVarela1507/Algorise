import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ModuloConcluido } from '@/components/atividades/ModuloConcluido'

describe('ModuloConcluido', () => {
  it('comemora o módulo e diz qual abriu', () => {
    render(
      <ModuloConcluido titulo="Primeiro print()" xpGanho={40} proximo={3} aoContinuar={vi.fn()} />,
    )

    expect(screen.getByRole('dialog', { name: 'Mandou bem!' })).toBeInTheDocument()
    expect(screen.getByText(/O módulo 3 já está liberado/)).toBeInTheDocument()
    expect(screen.getByText('Você ganhou 40 XP')).toBeInTheDocument()
  })

  it('volta para o caminho pelo botão, que já vem com o foco', async () => {
    const continuar = vi.fn()
    render(<ModuloConcluido titulo="Listas" xpGanho={20} proximo={8} aoContinuar={continuar} />)

    const botao = screen.getByRole('button', { name: /Voltar para o caminho/ })
    expect(botao).toHaveFocus()
    await userEvent.click(botao)

    expect(continuar).toHaveBeenCalledOnce()
  })

  it('Esc também volta', async () => {
    const continuar = vi.fn()
    render(<ModuloConcluido titulo="Listas" xpGanho={20} proximo={8} aoContinuar={continuar} />)

    await userEvent.keyboard('{Escape}')

    expect(continuar).toHaveBeenCalledOnce()
  })

  it('no último módulo, comemora a trilha inteira', () => {
    render(<ModuloConcluido titulo="Projeto" xpGanho={60} proximo={null} aoContinuar={vi.fn()} />)

    expect(screen.getByRole('dialog', { name: 'Você zerou a trilha!' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Ver a trilha completa/ })).toBeInTheDocument()
  })

  it('sem XP novo (passo refeito), não mostra o +0', () => {
    render(<ModuloConcluido titulo="Listas" xpGanho={0} proximo={8} aoContinuar={vi.fn()} />)

    expect(screen.queryByText(/XP/)).not.toBeInTheDocument()
  })
})
