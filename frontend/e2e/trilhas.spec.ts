import { expect, test } from '@playwright/test'
import { criarConta, entrar } from './apoio'

/**
 * A tela de Trilhas lendo a API (telas 24 e 25).
 *
 * É o teste que garante que o que está no banco chega à tela: catálogo, busca e
 * filtro por período acontecem no servidor, então um desencontro de nome de
 * parâmetro quebraria tudo em silêncio no navegador.
 */

test.beforeEach(async ({ page, request }) => {
  const conta = await criarConta(request)
  await entrar(page, conta)
  await page.goto('/trilhas')
})

test('mostra a trilha que está no banco', async ({ page }) => {
  // Vem do seed (`python -m app.seeds`).
  await expect(page.getByRole('heading', { name: 'Introdução Python' })).toBeVisible()
  await expect(page.getByText('0/10')).toBeVisible()
})

test('a busca filtra pelo servidor', async ({ page }) => {
  await page.getByLabel('Buscar trilhas').fill('Introdução')
  await expect(page.getByRole('heading', { name: 'Introdução Python' })).toBeVisible()

  await page.getByLabel('Buscar trilhas').fill('xxxxxxxx')
  await expect(page.getByText('Nenhuma trilha encontrada')).toBeVisible()
})

test('o filtro por período devolve a página certa', async ({ page }) => {
  await page.getByLabel('Filtrar por período').click()

  // A trilha do seed é do 1º período: marcar o 5º tem de esvaziar a lista.
  await page.getByRole('button', { name: '5º Período' }).click()
  await expect(page.getByText('Nenhuma trilha encontrada')).toBeVisible()

  await page.getByRole('button', { name: '1º Período' }).click()
  await expect(page.getByRole('heading', { name: 'Introdução Python' })).toBeVisible()
})
