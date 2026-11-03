import { expect, test } from '@playwright/test'
import { API, criarConta, entrar } from './apoio'

/**
 * Exercícios de prática do passo (#201). A geração pela IA não roda no E2E (o
 * provedor é o `Eco`): a rota responde daqui, primeiro gerando e depois pronta,
 * e o que se confere é a tela.
 */

test('o aluno pede exercícios e vê a dica e a resposta', async ({ page, request }) => {
  let pedidos = 0
  await page.route(`${API}/trilhas/introducao-python/passos/1/exercicios`, (route) => {
    pedidos += 1
    return route.fulfill({
      json:
        pedidos === 1
          ? { status: 'gerando', exercicios: [] }
          : {
              status: 'pronto',
              exercicios: [
                {
                  enunciado: 'Mostre a versão do Python no terminal.',
                  resposta_esperada: 'python --version',
                  dica: 'É um comando com dois hifens.',
                },
              ],
            },
    })
  })
  await entrar(page, await criarConta(request))
  await page.goto('/trilhas/introducao-python/questao/1')

  // Abrir o passo não gera nada: só o pedido do aluno.
  await expect(page.getByRole('heading', { name: 'Pratique' })).toBeVisible()
  expect(pedidos).toBe(0)

  await page.getByRole('button', { name: 'Praticar com exercícios' }).click()

  await expect(page.getByText('Criando exercícios sobre este passo…')).toBeVisible()
  await expect(page.getByText('1. Mostre a versão do Python no terminal.')).toBeVisible({
    timeout: 10_000,
  })
  await page.getByText('Ver resposta').click()
  await expect(page.getByText('python --version', { exact: true })).toBeVisible()
})
