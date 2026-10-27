import { expect, test } from '@playwright/test'
import { API, cabecalhoDe, criarConta, entrar } from './apoio'

/**
 * Perfil (#27): modo de trilha, foto e preferências que acompanham a conta.
 *
 * Os três cruzam a fronteira entre frontend e API de um jeito que o teste
 * unitário não pega: o modo muda o que a API libera nas trilhas, a foto volta
 * como caminho da API (que mora em outra origem) e a preferência precisa
 * chegar a um navegador que nunca a viu.
 */

// PNG de 1x1, o menor arquivo que o backend aceita como imagem.
const PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
  'base64',
)

test('trocar para o modo livre pelo perfil abre todos os passos', async ({ page, request }) => {
  const conta = await criarConta(request)
  await entrar(page, conta)
  const cabecalho = await cabecalhoDe(request, conta)
  const estados = async () => {
    const resposta = await request.get(`${API}/trilhas/introducao-python`, { headers: cabecalho })
    const { modulos } = (await resposta.json()) as { modulos: { status: string }[] }
    return modulos.map((modulo) => modulo.status)
  }

  // Guiada, o padrão: só o primeiro passo está aberto.
  expect(await estados()).toContain('bloqueado')

  await page.goto('/perfil')
  await page.getByRole('radio', { name: /Modo trilha livre/ }).click()
  await expect(page.getByText('Modo trilha livre ativado')).toBeVisible()

  // Conferido pela API, e não pelo mapa da trilha: a tela da trilha ainda
  // desenha os módulos a partir do mock, e não do servidor.
  expect(await estados()).not.toContain('bloqueado')
})

test('a foto enviada aparece no perfil e pode ser removida', async ({ page, request }) => {
  await entrar(page, await criarConta(request))
  await page.goto('/perfil')

  await page.getByTestId('entrada-avatar').setInputFiles({
    name: 'foto.png',
    mimeType: 'image/png',
    buffer: PNG,
  })

  await expect(page.getByText('Foto atualizada')).toBeVisible()
  // A imagem só entra no lugar das iniciais depois de carregar, então ela
  // aparecer prova que a URL relativa da API foi resolvida para a origem certa.
  const foto = page.locator('img[src*="/media/avatares/"]')
  await expect(foto).toBeVisible()

  await page.getByRole('button', { name: 'Remover foto do perfil' }).click()
  await expect(page.getByText('Foto removida')).toBeVisible()
  await expect(foto).toHaveCount(0)
})

test('arquivo que não é imagem é recusado com o motivo', async ({ page, request }) => {
  await entrar(page, await criarConta(request))
  await page.goto('/perfil')

  await page.getByTestId('entrada-avatar').setInputFiles({
    name: 'foto.png',
    mimeType: 'image/png',
    buffer: Buffer.from('%PDF-1.7\n%%EOF'),
  })

  await expect(page.getByText('Envie uma imagem PNG, JPEG ou WebP.')).toBeVisible()
})

test('alto contraste ligado num aparelho vale no outro', async ({ browser, page, request }) => {
  const conta = await criarConta(request)
  await entrar(page, conta)
  await page.goto('/configuracoes')
  const salvou = page.waitForResponse(
    (resposta) => resposta.url().includes('/usuarios/me/preferencias') && resposta.ok(),
  )
  await page.getByRole('radiogroup', { name: 'Fundo de alto contraste' }).getByText('Sim').click()
  await salvou

  // Outro contexto é outro navegador: nada do localStorage do primeiro.
  const outroAparelho = await browser.newContext()
  const outraPagina = await outroAparelho.newPage()
  await entrar(outraPagina, conta)

  await expect(outraPagina.locator('html')).toHaveAttribute('data-high-contrast', 'true')
  await outroAparelho.close()
})
