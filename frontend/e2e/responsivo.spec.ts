import { expect, test } from '@playwright/test'
import { criarConta, entrar } from './apoio'

/**
 * Smoke de responsividade, rodado no projeto `celular` (Pixel 7).
 *
 * Não é teste visual: é a verificação de que nada some nem transborda na
 * largura de celular, que é por onde a maior parte dos alunos entra.
 */

async function semRolagemHorizontal(page: import('@playwright/test').Page) {
  return page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
  )
}

test('a tela de login cabe na largura do celular', async ({ page }) => {
  await page.goto('/login')

  await expect(page.getByRole('button', { name: 'Entrar' })).toBeVisible()
  expect(await semRolagemHorizontal(page)).toBeTruthy()
})

test('o cadastro cabe na largura do celular', async ({ page }) => {
  await page.goto('/cadastro')

  await expect(page.getByLabel('Nome de usuário')).toBeVisible()
  expect(await semRolagemHorizontal(page)).toBeTruthy()
})

test('a home cabe na largura do celular depois de entrar', async ({ page, request }) => {
  const conta = await criarConta(request)
  await entrar(page, conta)

  expect(await semRolagemHorizontal(page)).toBeTruthy()
})

test('o alvo de toque do botão principal tem tamanho suficiente', async ({ page }) => {
  await page.goto('/login')

  const caixa = await page.getByRole('button', { name: 'Entrar' }).boundingBox()

  // 44px é o mínimo recomendado pelo WCAG 2.2 para alvo de toque.
  expect(caixa?.height ?? 0).toBeGreaterThanOrEqual(44)
})
