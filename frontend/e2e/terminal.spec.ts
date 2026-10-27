import { expect, test } from '@playwright/test'
import { criarConta, entrar } from './apoio'

/**
 * As atividades de terminal (telas 28 a 33), com o Xterm rodando de verdade.
 *
 * É o que o teste de unidade não alcança: no jsdom o Xterm não desenha, então
 * só aqui dá para saber se digitar no terminal funciona mesmo. O passo vem do
 * seed (`introducao-python`), e o passo 1 nasce liberado.
 */

test.beforeEach(async ({ page, request }) => {
  const conta = await criarConta(request)
  await entrar(page, conta)
  await page.goto('/trilhas/introducao-python/questao/1')
})

test('o terminal responde ao que o aluno digita', async ({ page }) => {
  await expect(page.getByRole('heading', { name: 'Iniciando no Python' })).toBeVisible()

  // Clica no terminal e digita nele, não no campo alternativo: é o Xterm que
  // está sendo verificado aqui.
  await page.locator('.xterm-screen').click()
  await page.keyboard.type('winget install Python.Python.3.14')
  await page.keyboard.press('Enter')

  // A saída é longa e roteirizada; o log acessível espelha o que saiu na tela.
  const log = page.getByRole('log', { name: 'Saída do terminal' })
  await expect(log).toContainText('Instalação concluída com êxito', { timeout: 15_000 })
  // O "correto" vem do servidor (#30), e só depois de o roteiro terminar de
  // escrever: a saída deste comando leva ~3s sozinha.
  await expect(page.getByText('Comando correto!')).toBeVisible({ timeout: 15_000 })
})

test('o Avançar só libera com o comando certo', async ({ page }) => {
  const avancar = page.getByRole('button', { name: 'Avançar' })
  await expect(avancar).toBeDisabled()

  await page.getByLabel('Digite o comando da atividade').fill('comando-errado')
  await page.keyboard.press('Enter')

  await expect(page.getByText(/Tentativas: 1/)).toBeVisible()
  await expect(avancar).toBeDisabled()
})

test('concluir o passo leva ao próximo e soma no progresso da trilha', async ({ page }) => {
  // As duas atividades de terminal do passo 1 do seed.
  await page.getByLabel('Digite o comando da atividade').fill('winget install Python.Python.3.14')
  await page.keyboard.press('Enter')
  const avancar = page.getByRole('button', { name: 'Avançar' })
  await expect(avancar).toBeEnabled({ timeout: 15_000 })
  await avancar.click()

  await page.getByLabel('Digite o comando da atividade').fill('python --version')
  await page.keyboard.press('Enter')
  await expect(avancar).toBeEnabled()
  await avancar.click()

  // Quem fechou o passo foi a API, e foi ela que disse qual é o próximo.
  await expect(page).toHaveURL('/trilhas/introducao-python/questao/2')

  // E o catálogo já mostra o passo fechado, sem recarregar na mão.
  await page.goto('/trilhas')
  await expect(page.getByText('1/10')).toBeVisible()
})

test('encadeia as duas atividades do passo', async ({ page }) => {
  await expect(page.getByRole('progressbar', { name: 'Atividade 1 de 2' })).toBeVisible()

  await page.getByLabel('Digite o comando da atividade').fill('winget install Python.Python.3.14')
  await page.keyboard.press('Enter')
  const avancar = page.getByRole('button', { name: 'Avançar' })
  await expect(avancar).toBeEnabled({ timeout: 15_000 })
  await avancar.click()

  // Segunda atividade: o terminal recomeça limpo.
  await expect(page.getByRole('progressbar', { name: 'Atividade 2 de 2' })).toBeVisible()
  await expect(avancar).toBeDisabled()

  await page.getByLabel('Digite o comando da atividade').fill('python --version')
  await page.keyboard.press('Enter')
  await expect(avancar).toBeEnabled()
  await avancar.click()

  // Fim do passo: a API fecha o passo e manda para o próximo.
  await expect(page).toHaveURL('/trilhas/introducao-python/questao/2')
})

test('o erro do protótipo mostra a dica do python -h', async ({ page }) => {
  // Vai para a segunda atividade pelo caminho normal.
  await page.getByLabel('Digite o comando da atividade').fill('winget install Python.Python.3.14')
  await page.keyboard.press('Enter')
  await expect(page.getByRole('button', { name: 'Avançar' })).toBeEnabled({ timeout: 15_000 })
  await page.getByRole('button', { name: 'Avançar' }).click()

  await page.getByLabel('Digite o comando da atividade').fill('python ---version')
  await page.keyboard.press('Enter')

  const log = page.getByRole('log', { name: 'Saída do terminal' })
  await expect(log).toContainText('unknown option ---version')
  await expect(log).toContainText('python -h')
})

test('passo bloqueado não entrega o conteúdo', async ({ page }) => {
  await page.goto('/trilhas/introducao-python/questao/3')

  await expect(page.getByText(/Conclua o passo anterior/)).toBeVisible()
})
