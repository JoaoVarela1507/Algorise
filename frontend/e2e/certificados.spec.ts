import { expect, test } from '@playwright/test'
import { API, criarConta, entrar } from './apoio'

/**
 * Certificados (tela 20) e a validação pública (#32). O seed não tem trilha de
 * parceiro, então a lista vem do teste; a validação de um código que não existe
 * passa pelo servidor de verdade.
 */

const LISTA = [
  {
    periodo: 1,
    itens: [
      {
        trilha_id: 1,
        slug: 'git',
        nome: 'Git',
        disciplina: 'Ferramentas',
        parceiro: 'UFRPE',
        carga_horaria: 20,
        total_modulos: 3,
        concluidos: 3,
        estado: 'liberado',
        certificado_id: 7,
      },
      {
        trilha_id: 2,
        slug: 'sql',
        nome: 'SQL',
        disciplina: 'Banco de Dados',
        parceiro: 'UFRPE',
        carga_horaria: null,
        total_modulos: 4,
        concluidos: 1,
        estado: 'bloqueado',
        certificado_id: null,
      },
    ],
  },
]

test('o aluno vê o certificado liberado e baixa o PDF', async ({ page, request }) => {
  await page.route(`${API}/certificados`, (route) => route.fulfill({ json: LISTA }))
  await page.route(`${API}/certificados/7/download`, (route) =>
    route.fulfill({
      body: '%PDF-1.4 falso',
      headers: {
        'content-type': 'application/pdf',
        'content-disposition': 'attachment; filename="certificado-ALG-2345-6789.pdf"',
        // O que o CORS da API manda: sem isso o navegador esconde o nome do arquivo.
        'access-control-expose-headers': 'Content-Disposition',
      },
    }),
  )
  await entrar(page, await criarConta(request))

  await page.goto('/certificados')

  await expect(page.getByText('1 de 2')).toBeVisible()
  await expect(page.getByText('1/4 módulos')).toBeVisible()
  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Baixar PDF' }).click()
  expect((await download).suggestedFilename()).toBe('certificado-ALG-2345-6789.pdf')
})

test('a validação pública confere o código sem login', async ({ page }) => {
  await page.route(`${API}/certificados/validar/ALG-2345-6789`, (route) =>
    route.fulfill({
      json: {
        codigo: 'ALG-2345-6789',
        nome_aluno: 'Ana Lima',
        nome_trilha: 'Git',
        disciplina: 'Ferramentas',
        carga_horaria: 20,
        parceiro: 'UFRPE',
        emitido_em: '2026-11-03T12:00:00Z',
      },
    }),
  )

  await page.goto('/validar')
  await page.getByRole('textbox', { name: 'Código do certificado' }).fill('ALG-2345-6789')
  await page.getByRole('button', { name: 'Conferir' }).click()

  await expect(page).toHaveURL('/validar/ALG-2345-6789')
  await expect(page.getByText('Certificado válido')).toBeVisible()
  await expect(page.getByText('Ana Lima')).toBeVisible()

  // Um código que não existe, direto no servidor.
  await page.goto('/validar/ALG-0000-0000')
  await expect(page.getByText('Nenhum certificado com esse código')).toBeVisible()
})
