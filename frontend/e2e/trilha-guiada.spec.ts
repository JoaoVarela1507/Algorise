import { expect, test, type Page, type Route } from '@playwright/test'
import { API, criarConta, entrar, EMENTA_DE_TESTE, pdfComTexto } from './apoio'

/**
 * Da ementa à trilha guiada (#38): revisar os assuntos, confirmar e ver a trilha.
 *
 * O upload no onboarding é de verdade. A leitura dos assuntos, não: o E2E roda
 * com o provedor `Eco` e um catálogo vazio, então as rotas da ementa e da
 * trilha guiada respondem daqui. O que o servidor faz com elas está no pytest
 * (`test_ementa_assuntos.py` e `test_trilha_guiada.py`); aqui é a tela.
 */

const EMENTA = {
  id: 1,
  status: 'processada',
  status_assuntos: 'prontos',
  nome_original: 'ementa.pdf',
  criado_em: '2026-10-28T12:00:00Z',
}

const ASSUNTOS = {
  status_assuntos: 'prontos',
  disciplinas: [
    {
      nome: 'Introdução à Programação',
      periodo: 1,
      carga_horaria: 60,
      assuntos: [
        { texto: 'Laços', situacao: 'coberto', modulo: { id: 4, titulo: 'Laços', trilha_id: 1 } },
        { texto: 'Recursão', situacao: 'lacuna', status_lacuna: 'pendente' },
      ],
    },
  ],
}

const TRILHA_GUIADA = {
  ementa_id: 1,
  confirmada_em: '2026-10-28T12:05:00Z',
  nivel: 'baixo',
  total_modulos: 2,
  concluidos: 0,
  itens: [
    {
      tipo: 'modulo',
      disciplina: 'Introdução à Programação',
      periodo: 1,
      assuntos: [],
      base: true,
      modulo: {
        id: 1,
        titulo: 'Iniciando no Python',
        ordem: 1,
        trilha_slug: 'introducao-python',
        trilha_nome: 'Introdução Python',
        status: 'em-andamento',
      },
    },
    {
      tipo: 'modulo',
      disciplina: 'Introdução à Programação',
      periodo: 1,
      assuntos: ['Laços de repetição'],
      base: false,
      modulo: {
        id: 4,
        titulo: 'Laços',
        ordem: 4,
        trilha_slug: 'introducao-python',
        trilha_nome: 'Introdução Python',
        status: 'bloqueado',
      },
    },
    {
      tipo: 'lacuna',
      disciplina: 'Introdução à Programação',
      periodo: 1,
      assuntos: ['Recursão'],
      base: false,
      status_lacuna: 'pendente',
    },
  ],
}

const json = (route: Route, corpo: unknown, status = 200) =>
  route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(corpo) })

async function enviarEmentaNoOnboarding(page: Page) {
  await page.goto('/onboarding')
  await page.getByRole('button', { name: /^Baixo/ }).click()
  await page.getByRole('button', { name: 'Continuar' }).click()
  await page.getByRole('button', { name: /^Guiada/ }).click()
  await page.getByRole('button', { name: 'Continuar' }).click()
  await page.getByRole('combobox', { name: /universidade\/faculdade/i }).fill('UFRPE')
  await page.locator('#grade-curricular').setInputFiles({
    name: 'ementa.pdf',
    mimeType: 'application/pdf',
    buffer: pdfComTexto(EMENTA_DE_TESTE),
  })
  await page.getByRole('button', { name: 'Continuar' }).click()
}

test('revisar os assuntos, confirmar e ver a trilha guiada', async ({ page, request }) => {
  // A primeira consulta pega a leitura ainda rodando; a tela espera e pergunta de novo.
  let consultas = 0
  await page.route(`${API}/ementas/atual`, (route) =>
    json(route, { ...EMENTA, status_assuntos: consultas++ === 0 ? 'processando' : 'prontos' }),
  )
  await page.route(`${API}/ementas/1/assuntos`, (route) => {
    if (route.request().method() === 'PUT') {
      const { disciplinas } = route.request().postDataJSON()
      return json(route, {
        ...ASSUNTOS,
        disciplinas: [
          {
            ...ASSUNTOS.disciplinas[0],
            assuntos: disciplinas[0].assuntos.map((texto: string) => ({
              texto,
              situacao: 'coberto',
            })),
          },
        ],
      })
    }
    return json(route, ASSUNTOS)
  })
  const revisoes: unknown[] = []
  page.on('request', (pedido) => {
    if (pedido.method() === 'PUT') revisoes.push(pedido.postDataJSON())
  })
  await page.route(`${API}/ementas/1/confirmar`, (route) =>
    json(route, { ...EMENTA, confirmada_em: TRILHA_GUIADA.confirmada_em }),
  )
  await page.route(`${API}/trilha-guiada`, (route) => json(route, TRILHA_GUIADA))

  await entrar(page, await criarConta(request))
  await enviarEmentaNoOnboarding(page)

  await expect(page).toHaveURL('/trilha-guiada/revisao')
  await expect(page.getByText('Lendo sua ementa…')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Introdução à Programação' })).toBeVisible({
    timeout: 10_000,
  })
  await expect(page.getByText('No catálogo')).toBeVisible()
  await expect(page.getByText('Em preparação')).toBeVisible()

  await page
    .getByRole('textbox', { name: 'Assunto 1 de Introdução à Programação' })
    .fill('Laços de repetição')
  await page.getByRole('button', { name: 'Remover "Recursão"' }).click()
  await page.getByRole('button', { name: 'Confirmar e gerar trilha' }).click()

  await expect(page).toHaveURL('/trilha-guiada')
  expect(revisoes).toEqual([
    {
      disciplinas: [
        {
          nome: 'Introdução à Programação',
          periodo: 1,
          carga_horaria: 60,
          assuntos: ['Laços de repetição'],
        },
      ],
    },
  ])

  await expect(page.getByRole('heading', { name: 'Sua trilha guiada' })).toBeVisible()
  await expect(page.getByText('0 de 2 módulos concluídos')).toBeVisible()
  // O passo liberado é um link para a atividade; o bloqueado, não.
  await expect(page.getByRole('link', { name: /Iniciando no Python/ })).toHaveAttribute(
    'href',
    '/trilhas/introducao-python/questao/1',
  )
  await expect(page.getByText('Base')).toBeVisible()
  await expect(page.getByRole('link', { name: /Laços/ })).toHaveCount(0)
  await expect(page.getByText('Recursão')).toBeVisible()
})

test('sem trilha guiada, a página leva à revisão da ementa', async ({ page, request }) => {
  await entrar(page, await criarConta(request))

  await page.goto('/trilha-guiada')

  await expect(page.getByText('Sua trilha guiada ainda não foi gerada')).toBeVisible()
  await page.getByRole('link', { name: 'Revisar a ementa' }).click()
  await expect(page.getByText('Você ainda não enviou uma ementa')).toBeVisible()
})
