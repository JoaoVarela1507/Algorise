/**
 * A revisão dos assuntos da ementa (#38): o que o aluno edita é o que vai ao
 * servidor, sem assunto em branco e sem disciplina vazia.
 */
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { RevisaoAssuntos } from '@/components/trilha-guiada/RevisaoAssuntos'
import { emLeitura, type DisciplinaLida } from '@/services/ementa'
import type { EmentaStatus } from '@/services/onboarding'

const LIDAS: DisciplinaLida[] = [
  {
    nome: 'Introdução à Programação',
    periodo: 1,
    carga_horaria: 60,
    assuntos: [
      { texto: 'Laços', situacao: 'coberto', modulo: { id: 4, titulo: 'Laços', trilha_id: 1 } },
      { texto: 'Recursão', situacao: 'lacuna', status_lacuna: 'pendente' },
    ],
  },
]

function revisao(props: Partial<Parameters<typeof RevisaoAssuntos>[0]> = {}) {
  const aoSalvar = vi.fn()
  const aoConfirmar = vi.fn()
  render(
    <RevisaoAssuntos
      disciplinas={LIDAS}
      salvando={false}
      erro={null}
      aoSalvar={aoSalvar}
      aoConfirmar={aoConfirmar}
      {...props}
    />,
  )
  return { aoSalvar, aoConfirmar }
}

describe('RevisaoAssuntos', () => {
  it('mostra o que está no catálogo e o que está em preparação', () => {
    revisao()

    expect(screen.getByRole('heading', { name: 'Introdução à Programação' })).toBeInTheDocument()
    expect(screen.getByText('1º período · 60 horas')).toBeInTheDocument()
    expect(screen.getByText('No catálogo')).toBeInTheDocument()
    expect(screen.getByText('Em preparação')).toBeInTheDocument()
    // Sem mudança, não há o que salvar; confirmar já pode.
    expect(screen.getByRole('button', { name: 'Salvar alterações' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Confirmar e gerar trilha' })).toBeEnabled()
  })

  it('renomear, remover e acrescentar vão juntos ao salvar', () => {
    const { aoSalvar } = revisao()

    fireEvent.change(
      screen.getByRole('textbox', { name: 'Assunto 1 de Introdução à Programação' }),
      {
        target: { value: 'Laços de repetição' },
      },
    )
    expect(screen.getByText('Novo')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Remover "Recursão"' }))
    const novo = screen.getByRole('textbox', { name: 'Novo assunto em Introdução à Programação' })
    fireEvent.change(novo, { target: { value: '  Funções  ' } })
    fireEvent.submit(novo)
    fireEvent.click(screen.getByRole('button', { name: 'Salvar alterações' }))

    expect(aoSalvar).toHaveBeenCalledWith([
      {
        nome: 'Introdução à Programação',
        periodo: 1,
        carga_horaria: 60,
        assuntos: ['Laços de repetição', 'Funções'],
      },
    ])
  })

  it('confirmar diz se a lista mudou, para a tela salvar antes', () => {
    const { aoConfirmar } = revisao()
    fireEvent.click(screen.getByRole('button', { name: 'Remover "Laços"' }))

    fireEvent.click(screen.getByRole('button', { name: 'Confirmar e gerar trilha' }))

    expect(aoConfirmar).toHaveBeenCalledWith(
      [expect.objectContaining({ assuntos: ['Recursão'] })],
      true,
    )
  })

  it('sem nenhum assunto, não deixa confirmar e diz o motivo', () => {
    revisao()
    fireEvent.click(screen.getByRole('button', { name: 'Remover "Laços"' }))
    fireEvent.click(screen.getByRole('button', { name: 'Remover "Recursão"' }))

    expect(screen.getByRole('alert')).toHaveTextContent('Deixe pelo menos um assunto')
    expect(screen.getByRole('button', { name: 'Confirmar e gerar trilha' })).toBeDisabled()
  })
})

describe('emLeitura', () => {
  const base = { id: 1, criado_em: '2026-10-28T00:00:00Z' } as EmentaStatus

  it.each([
    ['pendente', 'pendente', true],
    ['processando', 'pendente', true],
    ['processada', 'processando', true],
    ['processada', 'prontos', false],
    ['processada', 'falhou', false],
    ['falhou', 'pendente', false],
  ] as const)('PDF %s e assuntos %s: %s', (status, statusAssuntos, esperado) => {
    expect(emLeitura({ ...base, status, status_assuntos: statusAssuntos })).toBe(esperado)
  })
})
