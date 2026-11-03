import { expect, test } from '@playwright/test'
import { criarConta, entrar } from './apoio'

/**
 * Chat com o tutor (#11 e #36), passando pela API de verdade.
 *
 * O backend do E2E sobe com `IA_PROVEDOR=eco`, que responde "Você perguntou:
 * <pergunta>" sem IA nenhuma: o CI não tem o Ollama, e o que se testa aqui é o
 * caminho tela → API → streaming → tela, não a qualidade da resposta.
 */

test('pergunta vai pelo WebSocket, a resposta aparece e a conversa continua', async ({
  page,
  request,
}) => {
  // O que a página manda pelo socket, e o aviso de que ele autenticou (#36).
  const enviados: Record<string, unknown>[] = []
  const autenticou = new Promise<void>((pronto) => {
    page.on('websocket', (ws) => {
      if (!ws.url().endsWith('/api/v1/ws')) return
      ws.on('framesent', ({ payload }) => {
        enviados.push(JSON.parse(String(payload)) as Record<string, unknown>)
      })
      ws.on('framereceived', ({ payload }) => {
        if (String(payload).includes('"autenticado"')) pronto()
      })
    })
  })
  await entrar(page, await criarConta(request))
  await page.goto('/chat')
  await autenticou

  await page.getByRole('textbox', { name: 'Mensagem', exact: true }).fill('O que é um laço for?')
  await page.getByRole('button', { name: 'Enviar mensagem' }).click()
  await expect(page.getByText('Você perguntou: O que é um laço for?')).toBeVisible()

  // A segunda vai na mesma conversa da API: é assim que o tutor tem contexto.
  await page.getByRole('textbox', { name: 'Mensagem', exact: true }).fill('E o while?')
  await page.getByRole('button', { name: 'Enviar mensagem' }).click()
  await expect(page.getByText('Você perguntou: E o while?')).toBeVisible()

  const perguntas = enviados.filter((m) => m.tipo === 'chat.mensagem.enviar')
  expect(perguntas).toHaveLength(2)
  expect(perguntas[0]).toMatchObject({ conversa_id: null, conteudo: 'O que é um laço for?' })
  expect(perguntas[1].conversa_id).toEqual(expect.any(Number))
})

test('sem WebSocket, a pergunta cai no SSE', async ({ page, request }) => {
  // Rede que bloqueia WebSocket: o socket fecha na hora, e o chat usa o POST.
  await page.routeWebSocket('**/api/v1/ws', (ws) => ws.close())
  await entrar(page, await criarConta(request))
  await page.goto('/chat')

  const pedido = page.waitForRequest((p) => p.url().endsWith('/api/v1/chat/mensagens'))
  await page.getByRole('textbox', { name: 'Mensagem', exact: true }).fill('O que é um laço for?')
  await page.getByRole('button', { name: 'Enviar mensagem' }).click()

  expect((await pedido).postDataJSON()).toMatchObject({ conversa_id: null })
  await expect(page.getByText('Você perguntou: O que é um laço for?')).toBeVisible()
})

test('tutor fora do ar mostra o motivo na conversa', async ({ page, request }) => {
  // Pelo SSE, onde dá para simular o 503: o socket fica bloqueado.
  await page.routeWebSocket('**/api/v1/ws', (ws) => ws.close())
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
