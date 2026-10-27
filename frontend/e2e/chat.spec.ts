import { expect, test } from '@playwright/test'
import { criarConta, entrar } from './apoio'

/**
 * Chat com o tutor (#11), passando pela API de verdade.
 *
 * O backend do E2E sobe com `IA_PROVEDOR=eco`, que responde "Você perguntou:
 * <pergunta>" sem IA nenhuma: o CI não tem o Ollama, e o que se testa aqui é o
 * caminho tela → API → streaming → tela, não a qualidade da resposta.
 */

test('pergunta chega à API, a resposta aparece e a conversa continua', async ({
  page,
  request,
}) => {
  await entrar(page, await criarConta(request))
  await page.goto('/chat')

  const primeira = page.waitForRequest((pedido) => pedido.url().endsWith('/api/v1/chat/mensagens'))
  await page.getByRole('textbox', { name: 'Mensagem', exact: true }).fill('O que é um laço for?')
  await page.getByRole('button', { name: 'Enviar mensagem' }).click()

  expect((await primeira).postDataJSON()).toMatchObject({
    conversa_id: null,
    conteudo: 'O que é um laço for?',
  })
  await expect(page.getByText('Você perguntou: O que é um laço for?')).toBeVisible()

  // A segunda vai na mesma conversa da API: é assim que o tutor tem contexto.
  const segunda = page.waitForRequest((pedido) => pedido.url().endsWith('/api/v1/chat/mensagens'))
  await page.getByRole('textbox', { name: 'Mensagem', exact: true }).fill('E o while?')
  await page.getByRole('button', { name: 'Enviar mensagem' }).click()

  const corpo = (await segunda).postDataJSON() as { conversa_id: number | null }
  expect(corpo.conversa_id).toEqual(expect.any(Number))
  await expect(page.getByText('Você perguntou: E o while?')).toBeVisible()
})

test('tutor fora do ar mostra o motivo na conversa', async ({ page, request }) => {
  await entrar(page, await criarConta(request))
  // O 503 é o que a API responde com o Ollama fora; aqui ele é simulado, porque
  // o backend do E2E usa o provedor de teste, que nunca cai.
  await page.route('**/api/v1/chat/mensagens', (rota) =>
    rota.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({
        erro: {
          code: 'ia_indisponivel',
          message: 'O tutor está fora do ar agora. Tente de novo em instantes.',
          details: null,
          request_id: 'e2e',
        },
      }),
    }),
  )
  await page.goto('/chat')

  await page.getByRole('textbox', { name: 'Mensagem', exact: true }).fill('oi')
  await page.getByRole('button', { name: 'Enviar mensagem' }).click()

  await expect(page.getByText('O tutor está fora do ar agora.')).toBeVisible()
})
