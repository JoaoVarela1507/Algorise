import { expect, test } from '@playwright/test'
import { API, criarConta, entrar } from './apoio'

/**
 * Ranking servido do Redis, geral e por trilha (#12, telas 16 e 17).
 *
 * O que este teste cobre e nenhum outro cobre: o XP ganho numa atividade sair
 * do navegador, passar pela API, entrar no sorted set e voltar no ranking.
 */

test('o XP ganho na atividade aparece no ranking', async ({ page, request }) => {
  const conta = await criarConta(request)
  await entrar(page, conta)

  // Antes de pontuar, o aluno não está no ranking da trilha.
  const antes = await request.get(`${API}/ranking?trilha=introducao-python&limite=100`)
  const nomesAntes = ((await antes.json()).lista as { username: string }[]).map(
    (linha) => linha.username,
  )
  expect(nomesAntes).not.toContain(conta.username)

  // Faz a primeira atividade do passo 1.
  await page.goto('/trilhas/introducao-python/questao/1')
  await page.getByLabel('Digite o comando da atividade').fill('winget install Python.Python.3.14')
  await page.keyboard.press('Enter')
  await expect(page.getByRole('button', { name: 'Avançar' })).toBeEnabled({ timeout: 15_000 })

  const depois = await request.get(`${API}/ranking?trilha=introducao-python&limite=100`)
  const corpo = await depois.json()

  // Contagem exata não serve: os outros specs também pontuam nesta trilha, e
  // eles rodam em paralelo. O que importa é o aluno ter entrado, com o XP dele.
  const dele = (corpo.lista as { username: string; xp: number }[]).find(
    (linha) => linha.username === conta.username,
  )
  expect(dele).toBeDefined()
  expect(dele?.xp).toBe(10)
})

test('o ranking da trilha é diferente do geral', async ({ request }) => {
  const geral = await request.get(`${API}/ranking`)
  const daTrilha = await request.get(`${API}/ranking?trilha=introducao-python`)

  expect(geral.ok()).toBeTruthy()
  expect(daTrilha.ok()).toBeTruthy()
  // O geral conta todo mundo que tem conta; o da trilha, só quem pontuou nela.
  expect((await geral.json()).total).toBeGreaterThanOrEqual((await daTrilha.json()).total)
})

test('trilha inexistente no ranking devolve 404', async ({ request }) => {
  const resposta = await request.get(`${API}/ranking?trilha=nao-existe`)

  expect(resposta.status()).toBe(404)
  expect((await resposta.json()).erro.code).toBe('trilha_nao_encontrada')
})
