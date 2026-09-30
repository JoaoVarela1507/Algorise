import { expect, type APIRequestContext, type Page } from '@playwright/test'

/** Onde a API sobe no E2E (ver `webServer` no playwright.config.ts). */
export const API = 'http://127.0.0.1:8001/api/v1'

export interface Conta {
  username: string
  email: string
  senha: string
}

/**
 * Cria a conta pela API, e não pela tela.
 *
 * Passar pelo formulário de cadastro em todo teste transformaria qualquer
 * mudança nele em falha de todos os outros. O cadastro pela tela tem o teste
 * dele em `cadastro.spec.ts`.
 */
export async function criarConta(request: APIRequestContext): Promise<Conta> {
  // `randomUUID` e não `Math.random`: além de não repetir entre execuções
  // paralelas, evita o alerta de aleatoriedade fraca do CodeQL.
  const id = crypto.randomUUID().slice(0, 8)
  const conta: Conta = {
    username: `aluno_${id}`,
    email: `aluno_${id}@ufrpe.br`,
    senha: 'Trilha-Boa-2026',
  }

  const resposta = await request.post(`${API}/auth/register`, {
    data: { ...conta, aceite_termos: true },
  })
  expect(resposta.ok(), await resposta.text()).toBeTruthy()

  return conta
}

/** Entra pela tela de login e espera a home. */
export async function entrar(page: Page, conta: Conta): Promise<void> {
  await page.goto('/login')
  await page.getByLabel('Email').fill(conta.email)
  await page.getByLabel('Senha').fill(conta.senha)
  await page.getByRole('button', { name: 'Entrar' }).click()
  await expect(page).toHaveURL('/')
}
