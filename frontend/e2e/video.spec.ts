import { expect, test } from '@playwright/test'
import { API, criarConta, entrar } from './apoio'

/**
 * O vídeo do passo (#210): o player toca só o trecho do módulo, e o módulo
 * gerado automaticamente mostra o canal e pode ser reportado.
 *
 * O passo 1 da trilha do seed tem vídeo. O módulo automático não existe no
 * banco do E2E (a busca no YouTube não roda aqui), então a resposta do passo é
 * a do seed com os campos de um módulo automático, devolvida pelo teste.
 */

const PASSO = '/trilhas/introducao-python/questao/1'

test('o passo com vídeo mostra o player do YouTube', async ({ page, request }) => {
  await entrar(page, await criarConta(request))

  await page.goto(PASSO)

  const player = page.frameLocator('iframe[title^="Vídeo:"]').owner()
  await expect(player).toHaveAttribute(
    'src',
    'https://www.youtube-nocookie.com/embed/S9uPNppGsGo?rel=0',
  )
  // O módulo do seed não é automático: sem marca e sem reportar.
  await expect(page.getByText('Gerado automaticamente')).toHaveCount(0)
})

test('módulo gerado de um vídeo toca o trecho e pode ser reportado', async ({ page, request }) => {
  await page.route(`${API}/trilhas/introducao-python/passos/1`, async (route) => {
    const resposta = await route.fetch()
    const passo = await resposta.json()
    await route.fulfill({
      response: resposta,
      json: {
        ...passo,
        inicio_segundos: 60.4,
        fim_segundos: 599.2,
        origem: 'youtube',
        canal: 'Prof. Ana',
      },
    })
  })
  const reportes: string[] = []
  await page.route(`${API}/trilhas/introducao-python/passos/1/reportar`, (route) => {
    reportes.push(route.request().method())
    return route.fulfill({ json: { reportes: 1, removido: false } })
  })
  await entrar(page, await criarConta(request))

  await page.goto(PASSO)

  await expect(page.locator('iframe[title^="Vídeo:"]')).toHaveAttribute(
    'src',
    'https://www.youtube-nocookie.com/embed/S9uPNppGsGo?rel=0&start=60&end=600',
  )
  await expect(page.getByText('Gerado automaticamente')).toBeVisible()
  await expect(page.getByText('Vídeo de Prof. Ana')).toBeVisible()

  await page.getByRole('button', { name: 'Reportar vídeo' }).click()

  await expect(page.getByRole('status').filter({ hasText: 'Obrigado!' })).toBeVisible()
  expect(reportes).toEqual(['POST'])
})
