import { expect, test } from '@playwright/test'
import { criarConta, entrar } from './apoio'

/**
 * Acessibilidade das Configurações (tela 37).
 *
 * Fonte grande e alto contraste são requisito do projeto, não enfeite: o que se
 * verifica aqui é que a escolha chega ao `<html>` (é de lá que os tokens de
 * tema saem) e que ela sobrevive a recarregar a página.
 */

test.beforeEach(async ({ page, request }) => {
  const conta = await criarConta(request)
  await entrar(page, conta)
  await page.goto('/configuracoes')
})

test('fonte grande vale para o app inteiro e sobrevive ao recarregar', async ({ page }) => {
  const html = page.locator('html')
  await expect(html).toHaveAttribute('data-font-size', 'normal')

  await page.getByRole('radiogroup', { name: 'Tamanho da fonte' }).getByText('Alta').click()

  await expect(html).toHaveAttribute('data-font-size', 'alta')

  await page.reload()
  await expect(html).toHaveAttribute('data-font-size', 'alta')
})

test('alto contraste liga e sobrevive ao recarregar', async ({ page }) => {
  const html = page.locator('html')
  await expect(html).toHaveAttribute('data-high-contrast', 'false')

  await page.getByRole('radiogroup', { name: 'Fundo de alto contraste' }).getByText('Sim').click()

  await expect(html).toHaveAttribute('data-high-contrast', 'true')

  await page.reload()
  await expect(html).toHaveAttribute('data-high-contrast', 'true')
})

test('reduzir animações liga', async ({ page }) => {
  await page.getByRole('radiogroup', { name: 'Reduzir animações' }).getByText('Sim').click()

  await expect(page.locator('html')).toHaveAttribute('data-reduzir-animacoes', 'true')
})

test('os controles são alcançáveis por leitor de tela', async ({ page }) => {
  for (const nome of ['Tamanho da fonte', 'Fundo de alto contraste', 'Reduzir animações']) {
    const grupo = page.getByRole('radiogroup', { name: nome })
    await expect(grupo).toBeVisible()
    // Um dos botões precisa estar marcado, senão o leitor não anuncia o estado.
    await expect(grupo.getByRole('radio', { checked: true })).toHaveCount(1)
  }
})
