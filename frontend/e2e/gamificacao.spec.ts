import { expect, test } from '@playwright/test'
import { API, cabecalhoDe, criarConta, entrar } from './apoio'

/**
 * XP, nível e streak de ponta a ponta (#31, telas 16 e 20).
 *
 * O que só aparece aqui: abrir a home faz o check-in do dia, e acertar uma
 * atividade no navegador move o XP pela API.
 */

test('abrir a home registra o acesso do dia', async ({ page, request }) => {
  const conta = await criarConta(request)
  const cabecalho = await cabecalhoDe(request, conta)

  const antes = await (await request.get(`${API}/gamificacao/me`, { headers: cabecalho })).json()
  expect(antes.streak_dias).toBe(0)

  await entrar(page, conta)

  await expect
    .poll(async () => {
      const painel = await request.get(`${API}/gamificacao/me`, { headers: cabecalho })
      return (await painel.json()).streak_dias
    })
    .toBe(1)
})

test('o aluno começa no nível 1 e o XP da atividade entra no painel', async ({ page, request }) => {
  const conta = await criarConta(request)
  const cabecalho = await cabecalhoDe(request, conta)

  const inicial = await (await request.get(`${API}/gamificacao/me`, { headers: cabecalho })).json()
  expect(inicial).toMatchObject({ nivel: 1, xp_total: 0 })

  await entrar(page, conta)
  await page.goto('/trilhas/introducao-python/questao/1')
  await page.getByLabel('Digite o comando da atividade').fill('winget install Python.Python.3.14')
  await page.keyboard.press('Enter')
  await expect(page.getByRole('button', { name: 'Avançar' })).toBeEnabled({ timeout: 15_000 })

  const depois = await (await request.get(`${API}/gamificacao/me`, { headers: cabecalho })).json()
  expect(depois.xp_total).toBe(10)
  // A barra de progresso da tela 16 fecha a conta com a curva.
  expect(depois.xp_no_nivel + depois.xp_para_o_proximo).toBeGreaterThan(depois.xp_total)
})

test('o painel exige autenticação', async ({ request }) => {
  expect((await request.get(`${API}/gamificacao/me`)).status()).toBe(401)
})
