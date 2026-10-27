/**
 * O autocomplete do passo 3: escolher guarda o id, digitar o descarta.
 *
 * É essa troca que decide se o backend recebe `instituicao_id` ou o nome — e um
 * id que sobrevivesse a uma edição gravaria a faculdade errada.
 */
import { useState } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { CampoAutocomplete, type Sugestao } from '@/components/onboarding/CampoAutocomplete'
import type { Escolha } from '@/services/onboarding'

const SUGESTOES: Sugestao[] = [
  { id: 1, rotulo: 'Universidade Federal Rural de Pernambuco', detalhe: 'UFRPE' },
  { id: 2, rotulo: 'Universidade Federal de Pernambuco', detalhe: 'UFPE' },
]

function Campo({ aoMudar }: { aoMudar?: (valor: Escolha) => void }) {
  const [valor, setValor] = useState<Escolha>({ texto: '', id: null })
  return (
    <CampoAutocomplete
      id="instituicao"
      rotulo="Instituição"
      valor={valor}
      onChange={(novo) => {
        setValor(novo)
        aoMudar?.(novo)
      }}
      sugestoes={SUGESTOES}
    />
  )
}

describe('CampoAutocomplete', () => {
  it('escolher pelo teclado guarda o id da sugestão', () => {
    const mudancas: Escolha[] = []
    render(<Campo aoMudar={(v) => mudancas.push(v)} />)
    const campo = screen.getByRole('combobox', { name: 'Instituição' })

    fireEvent.change(campo, { target: { value: 'pern' } })
    expect(campo).toHaveAttribute('aria-expanded', 'true')
    fireEvent.keyDown(campo, { key: 'ArrowDown' })
    fireEvent.keyDown(campo, { key: 'Enter' })

    expect(mudancas[mudancas.length - 1]).toEqual({ texto: SUGESTOES[0].rotulo, id: 1 })
    expect(campo).toHaveValue(SUGESTOES[0].rotulo)
    expect(campo).toHaveAttribute('aria-expanded', 'false')
  })

  it('escolher com o mouse também guarda o id', () => {
    const mudancas: Escolha[] = []
    render(<Campo aoMudar={(v) => mudancas.push(v)} />)
    const campo = screen.getByRole('combobox', { name: 'Instituição' })

    fireEvent.change(campo, { target: { value: 'pern' } })
    fireEvent.mouseDown(screen.getByRole('option', { name: /UFPE$/ }))

    expect(mudancas[mudancas.length - 1]).toEqual({ texto: SUGESTOES[1].rotulo, id: 2 })
  })

  it('voltar a digitar depois de escolher descarta o id', () => {
    const mudancas: Escolha[] = []
    render(<Campo aoMudar={(v) => mudancas.push(v)} />)
    const campo = screen.getByRole('combobox', { name: 'Instituição' })
    fireEvent.change(campo, { target: { value: 'pern' } })
    fireEvent.mouseDown(screen.getAllByRole('option')[0])

    fireEvent.change(campo, { target: { value: 'Universidade Federal Rural' } })

    expect(mudancas[mudancas.length - 1]).toEqual({ texto: 'Universidade Federal Rural', id: null })
  })

  it('Escape fecha a lista sem escolher', () => {
    render(<Campo />)
    const campo = screen.getByRole('combobox', { name: 'Instituição' })
    fireEvent.change(campo, { target: { value: 'pern' } })

    fireEvent.keyDown(campo, { key: 'Escape' })

    expect(campo).toHaveAttribute('aria-expanded', 'false')
    expect(campo).toHaveValue('pern')
  })
})
