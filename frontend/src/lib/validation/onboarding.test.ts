/**
 * Schema do passo 3 do onboarding (#7).
 *
 * O que ele precisa garantir: só a instituição trava o aluno, e a ementa só é
 * obrigatória na trilha guiada.
 */
import { describe, expect, it } from 'vitest'
import { configuracaoTrilhaSchema, TAMANHO_MAXIMO_EMENTA } from '@/lib/validation/onboarding'

const valido = {
  instituicao: { texto: 'UFRPE', id: null },
  curso: { texto: '', id: null },
  periodo: '',
  ementa: null,
}

function pdf(tamanho = 10, nome = 'grade.pdf', tipo = 'application/pdf') {
  return new File([new Uint8Array(tamanho)], nome, { type: tipo })
}

function erros(ementaObrigatoria: boolean, dados: object) {
  const resultado = configuracaoTrilhaSchema(ementaObrigatoria).safeParse({ ...valido, ...dados })
  return resultado.success ? {} : resultado.error.flatten().fieldErrors
}

describe('configuração de trilha', () => {
  it('passa só com a instituição, sem curso, período nem ementa', () => {
    expect(erros(false, {})).toEqual({})
  })

  it('cobra a instituição, mesmo com espaços', () => {
    expect(erros(false, { instituicao: { texto: '   ', id: null } }).instituicao).toEqual([
      'Informe sua instituição de ensino.',
    ])
  })

  it('cobra a ementa só na trilha guiada', () => {
    expect(erros(true, {}).ementa).toEqual([
      'Na trilha guiada, envie a ementa para montarmos o seu plano de estudos.',
    ])
    expect(erros(true, { ementa: pdf() })).toEqual({})
  })

  it('recusa o que não é PDF pelo tipo e pelo nome', () => {
    expect(erros(false, { ementa: pdf(10, 'grade.docx', 'application/msword') }).ementa).toEqual([
      'Envie a ementa em PDF.',
    ])
    // Sem tipo (alguns sistemas não informam), vale a extensão.
    expect(erros(false, { ementa: pdf(10, 'GRADE.PDF', '') })).toEqual({})
  })

  it('recusa a ementa acima de 5 MB', () => {
    expect(erros(false, { ementa: pdf(TAMANHO_MAXIMO_EMENTA) })).toEqual({})
    expect(erros(false, { ementa: pdf(TAMANHO_MAXIMO_EMENTA + 1) }).ementa).toEqual([
      'A ementa precisa ter até 5 MB.',
    ])
  })
})
