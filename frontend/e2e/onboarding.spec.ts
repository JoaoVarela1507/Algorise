import { expect, test, type Page } from '@playwright/test'
import { API, cabecalhoDe, criarConta, entrar, EMENTA_DE_TESTE, pdfComTexto } from './apoio'

/**
 * Passo 3 do onboarding (#28) fora do caminho feliz do cadastro.
 *
 * Os dois casos que não podem travar o aluno: a faculdade dele não está no
 * catálogo, e a ementa que ele escolheu não é PDF.
 */

async function irParaOPasso3(page: Page, trilha: RegExp) {
  await page.goto('/onboarding')
  await page.getByRole('button', { name: /^Baixo/ }).click()
  await page.getByRole('button', { name: 'Continuar' }).click()
  await page.getByRole('button', { name: trilha }).click()
  await page.getByRole('button', { name: 'Continuar' }).click()
  await expect(page.getByText('Passo 3 de 3')).toBeVisible()
}

test('faculdade fora do catálogo, digitada, conclui o onboarding', async ({ page, request }) => {
  const conta = await criarConta(request)
  await entrar(page, conta)
  await irParaOPasso3(page, /^Livre/)

  await page
    .getByRole('combobox', { name: /universidade\/faculdade/i })
    .fill('Faculdade Nova do Agreste')
  await page.getByRole('combobox', { name: /curso de graduação/i }).fill('Engenharia de Software')
  await page.getByRole('button', { name: 'Continuar' }).click()

  await expect(page).toHaveURL('/')
  const perfil = await request.get(`${API}/usuarios/me`, {
    headers: await cabecalhoDe(request, conta),
  })
  expect(await perfil.json()).toMatchObject({
    instituicao: 'Faculdade Nova do Agreste',
    curso: 'Engenharia de Software',
    tipo_trilha: 'livre',
  })
})

test('ementa que não é PDF mostra o motivo e não perde o preenchido', async ({ page, request }) => {
  await entrar(page, await criarConta(request))
  await irParaOPasso3(page, /^Guiada/)
  const instituicao = page.getByRole('combobox', { name: /universidade\/faculdade/i })
  await instituicao.fill('UFRPE')
  await page.locator('#grade-curricular').setInputFiles({
    name: 'grade.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.from('não sou um pdf'),
  })

  await page.getByRole('button', { name: 'Continuar' }).click()

  await expect(page.getByRole('alert')).toContainText('Envie a ementa em PDF.')
  await expect(page).toHaveURL('/onboarding')
  await expect(instituicao).toHaveValue('UFRPE')

  // Trocar pelo arquivo certo e tentar de novo segue em frente.
  await page.locator('#grade-curricular').setInputFiles({
    name: 'grade.pdf',
    mimeType: 'application/pdf',
    buffer: pdfComTexto(EMENTA_DE_TESTE),
  })
  await page.getByRole('button', { name: 'Continuar' }).click()
  await expect(page).toHaveURL('/')
})

test('sem instituição nem ementa na guiada, o passo 3 diz o que falta', async ({
  page,
  request,
}) => {
  await entrar(page, await criarConta(request))
  await irParaOPasso3(page, /^Guiada/)

  await page.getByRole('button', { name: 'Continuar' }).click()

  // O foco vai para o primeiro campo com erro na ordem da tela, que é a ementa,
  // e cada erro fica ligado ao seu campo.
  const instituicao = page.getByRole('combobox', { name: /universidade\/faculdade/i })
  await expect(page.locator('#grade-curricular')).toBeFocused()
  await expect(page.locator('#grade-curricular')).toHaveAccessibleDescription(/envie a ementa/i)
  await expect(instituicao).toHaveAccessibleDescription('Informe sua instituição de ensino.')
  await expect(page).toHaveURL('/onboarding')

  // Arquivo que não é PDF: o aviso vem na hora, antes de qualquer envio.
  await page.locator('#grade-curricular').setInputFiles({
    name: 'grade.docx',
    mimeType: 'application/msword',
    buffer: Buffer.from('docx'),
  })
  await expect(page.locator('#grade-curricular')).toHaveAccessibleDescription(
    'Envie a ementa em PDF.',
  )
})
