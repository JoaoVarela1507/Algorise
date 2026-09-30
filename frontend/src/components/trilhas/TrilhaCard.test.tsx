/**
 * Testes do card de trilha (tela 24).
 *
 * O card tem três estados — em andamento, concluída e bloqueada — e o
 * bloqueado é o que mais erra: ele não pode virar link, senão o aluno entra
 * numa trilha que ainda não liberou.
 */
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { TrilhaCard } from '@/components/trilhas/TrilhaCard'
import type { TrilhaResumo } from '@/types/trilha'

const BASE: TrilhaResumo = {
  id: 'introducao-python',
  nome: 'Introdução a Python',
  categoria: 'Linguagens',
  periodo: 1,
  modulosConcluidos: 3,
  totalModulos: 10,
  motivo: 'Recomendação do Algorise',
  bloqueada: false,
}

function montar(mudancas: Partial<TrilhaResumo> = {}) {
  return render(
    <MemoryRouter>
      <TrilhaCard trilha={{ ...BASE, ...mudancas }} />
    </MemoryRouter>,
  )
}

describe('trilha disponível', () => {
  it('mostra nome, categoria, período e progresso', () => {
    montar()

    expect(screen.getByRole('heading', { name: 'Introdução a Python' })).toBeInTheDocument()
    expect(screen.getByText('Linguagens')).toBeInTheDocument()
    expect(screen.getByText('1º Período')).toBeInTheDocument()
    expect(screen.getByText('3/10')).toBeInTheDocument()
    expect(screen.getByText('30%')).toBeInTheDocument()
  })

  it('leva para a trilha', () => {
    montar()

    expect(screen.getByRole('link')).toHaveAttribute('href', '/trilhas/introducao-python/questao/1')
  })

  it('arredonda a porcentagem', () => {
    montar({ modulosConcluidos: 1, totalModulos: 3 })

    expect(screen.getByText('33%')).toBeInTheDocument()
  })

  it('mostra o motivo da recomendação', () => {
    montar({ recomendada: true, motivo: 'Combina com o seu período' })

    expect(screen.getByText('Combina com o seu período')).toBeInTheDocument()
  })
})

describe('trilha concluída', () => {
  it('chega a 100%', () => {
    montar({ modulosConcluidos: 10, totalModulos: 10 })

    expect(screen.getByText('100%')).toBeInTheDocument()
    expect(screen.getByText('10/10')).toBeInTheDocument()
  })
})

describe('trilha bloqueada', () => {
  it('não vira link', () => {
    montar({ bloqueada: true, requisito: 'Lógica de Programação' })

    expect(screen.queryByRole('link')).not.toBeInTheDocument()
    expect(screen.getByRole('button')).toHaveAttribute('aria-disabled', 'true')
  })

  it('explica o que falta, no texto e no rótulo acessível', () => {
    montar({ bloqueada: true, requisito: 'Lógica de Programação' })

    expect(screen.getByText(/para desbloquear/)).toHaveTextContent('Lógica de Programação')
    expect(screen.getByRole('button').getAttribute('aria-label')).toContain(
      'bloqueada. Conclua Lógica de Programação',
    )
  })

  it('esconde a barra de progresso', () => {
    montar({ bloqueada: true, requisito: 'Lógica de Programação' })

    expect(screen.queryByText('30%')).not.toBeInTheDocument()
  })
})
