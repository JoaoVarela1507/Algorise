/**
 * Testes dos stores Zustand.
 *
 * O que importa é o critério de aceite da #5: o que tem de sobreviver a uma
 * recarga vai para o armazenamento certo, e o rascunho de onboarding de um
 * aluno nunca aparece para outro.
 */
import { afterEach, describe, expect, it } from 'vitest'
import { useAccessibilityStore } from '@/stores/useAccessibilityStore'
import { useAuthStore } from '@/stores/useAuthStore'
import { temProgresso, useOnboardingStore } from '@/stores/useOnboardingStore'
import type { Usuario } from '@/types/usuario'

const ementa = new File(['conteúdo'], 'ementa.pdf', { type: 'application/pdf' })

function preencher() {
  useOnboardingStore.getState().salvarRascunho({
    passo: 3,
    nivel: 'medio',
    trilha: 'guiada',
    instituicao: { texto: 'UFRPE', id: 1 },
    curso: { texto: 'BCC', id: 2 },
    periodo: '3',
    ementa,
  })
}

function guardado(armazenamento: Storage, chave: string) {
  return JSON.parse(armazenamento.getItem(chave) ?? 'null')?.state
}

// Os stores vivem no módulo, entre um teste e outro: voltam ao começo.
afterEach(() => {
  useAccessibilityStore.setState(useAccessibilityStore.getInitialState(), true)
  useAuthStore.setState(useAuthStore.getInitialState(), true)
  useOnboardingStore.setState(useOnboardingStore.getInitialState(), true)
})

describe('useOnboardingStore', () => {
  it('guarda o rascunho na aba, sem a ementa', () => {
    useOnboardingStore.getState().vincularAluno('aluno-1')
    preencher()

    const salvo = guardado(sessionStorage, 'algorise:onboarding')
    expect(salvo.usuarioId).toBe('aluno-1')
    expect(salvo.rascunho).toMatchObject({ passo: 3, nivel: 'medio', periodo: '3' })
    // Um `File` não vira JSON: depois de recarregar, o aluno escolhe de novo.
    expect(salvo.rascunho.ementa).toBeNull()
    expect(localStorage.getItem('algorise:onboarding')).toBeNull()
  })

  it('mantém o rascunho quando o mesmo aluno volta', () => {
    useOnboardingStore.getState().vincularAluno('aluno-1')
    preencher()

    useOnboardingStore.getState().vincularAluno('aluno-1')

    expect(useOnboardingStore.getState().rascunho.passo).toBe(3)
  })

  it('descarta o rascunho quando entra outro aluno', () => {
    useOnboardingStore.getState().vincularAluno('aluno-1')
    preencher()

    useOnboardingStore.getState().vincularAluno('aluno-2')

    expect(temProgresso(useOnboardingStore.getState().rascunho)).toBe(false)
  })

  it('descarta o rascunho no logout', () => {
    useAuthStore.setState({ usuario: { id: 'aluno-1' } as Usuario })
    useOnboardingStore.getState().vincularAluno('aluno-1')
    preencher()

    useAuthStore.getState().logout()

    expect(useAuthStore.getState().usuario).toBeNull()
    expect(temProgresso(useOnboardingStore.getState().rascunho)).toBe(false)
  })
})

describe('useAccessibilityStore', () => {
  it('aplica a preferência no <html> e guarda no navegador', () => {
    useAccessibilityStore.getState().setTamanhoFonte('alta')
    useAccessibilityStore.getState().setAltoContraste(true)

    expect(document.documentElement).toHaveAttribute('data-font-size', 'alta')
    expect(document.documentElement).toHaveAttribute('data-high-contrast', 'true')
    expect(guardado(localStorage, 'algorise:acessibilidade')).toMatchObject({
      tamanhoFonte: 'alta',
      altoContraste: true,
    })
  })
})
