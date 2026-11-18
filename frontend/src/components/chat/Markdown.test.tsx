import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Markdown } from './Markdown'

describe('Markdown do chat', () => {
  afterEach(() => vi.useRealTimers())

  it('renderiza títulos, negrito e itálico sem mostrar a sintaxe crua', () => {
    const { container } = render(
      <Markdown texto={'### Exemplo do while\n\nUma pilha é *Last In, First Out* e **rápida**.'} />,
    )
    expect(screen.getByRole('heading', { name: 'Exemplo do while' })).toBeInTheDocument()
    expect(container.querySelector('em')).toHaveTextContent('Last In, First Out')
    expect(container.querySelector('strong')).toHaveTextContent('rápida')
    expect(container).not.toHaveTextContent('*')
    expect(container).not.toHaveTextContent('###')
  })

  it('renderiza listas, código em linha, citação e link seguro', () => {
    const { container } = render(
      <Markdown
        texto={
          '1. um\n2. dois\n   - aninhado\n\n> citação\n\nUse `print()` e [docs](https://exemplo.com).'
        }
      />,
    )
    expect(container.querySelectorAll('ol > li')).toHaveLength(2)
    expect(container.querySelector('ol ul li')).toHaveTextContent('aninhado')
    expect(container.querySelector('blockquote')).toHaveTextContent('citação')
    expect(container.querySelector('p code')).toHaveTextContent('print()')
    const link = screen.getByRole('link', { name: 'docs' })
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('não injeta HTML cru nem links javascript:', () => {
    const { container } = render(
      <Markdown
        texto={'<img src=x onerror="alert(1)"><script>x</script>\n\n[x](javascript:alert(1))'}
      />,
    )
    expect(container.querySelector('img')).toBeNull()
    expect(container.querySelector('script')).toBeNull()
    expect(container.querySelector('a')?.getAttribute('href') ?? '').not.toContain('javascript')
  })

  it('mostra bloco de código com rótulo da linguagem e realce', () => {
    const { container } = render(
      <Markdown texto={'```python\ndef soma(a, b):\n    return a + b\n```'} />,
    )
    expect(screen.getByText('Python')).toBeInTheDocument()
    expect(container.querySelector('pre .hljs-keyword')).toHaveTextContent('def')
  })

  it('aguenta uma cerca sem fechar durante o streaming', () => {
    const { container, rerender } = render(<Markdown texto={'Veja:\n\n```python\nfor i in ra'} />)
    expect(container.querySelector('pre')).toHaveTextContent('for i in ra')
    rerender(
      <Markdown texto={'Veja:\n\n```python\nfor i in range(3):\n    print(i)\n```\n\nPronto.'} />,
    )
    expect(container.querySelectorAll('pre')).toHaveLength(1)
    expect(screen.getByText('Pronto.')).toBeInTheDocument()
  })

  it('linguagem desconhecida ou ausente vira texto simples, sem erro', () => {
    render(<Markdown texto={'```foo\nabc\n```\n\n```\nxyz\n```'} />)
    expect(screen.getByText('foo')).toBeInTheDocument()
    expect(screen.getByText('Código')).toBeInTheDocument()
  })

  it('o botão Copiar manda o código para a área de transferência e avisa "Copiado!"', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    const user = userEvent.setup()
    // userEvent.setup() instala o próprio clipboard; o espião vem depois dele.
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    render(<Markdown texto={'```python\nprint("oi")\n```'} />)

    await user.click(screen.getByRole('button', { name: 'Copiar código' }))

    expect(writeText).toHaveBeenCalledWith('print("oi")')
    expect(await screen.findByText('Copiado!')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Código copiado' })).toBeInTheDocument()
  })

  it('volta para "Copiar" depois de 2 segundos', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    render(<Markdown texto={'```js\nlet a = 1\n```'} />)

    await user.click(screen.getByRole('button', { name: 'Copiar código' }))
    expect(await screen.findByText('Copiado!')).toBeInTheDocument()
    await vi.advanceTimersByTimeAsync(2100)
    expect(screen.getByText('Copiar')).toBeInTheDocument()
  })
})
