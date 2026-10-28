import { expect, test } from '@playwright/test'
import { API, EMENTA_DE_TESTE, pdfComTexto } from './apoio'

/**
 * O caminho que todo aluno percorre uma vez: criar conta, responder o
 * onboarding e cair na home já logado.
 *
 * É aqui que aparece o desencontro que teste de unidade não pega — o frontend
 * mandando um campo que a API não espera, a API respondendo num formato que o
 * frontend não lê, a rota mudando de lugar.
 */

function aluno() {
  // Cada execução cria uma conta nova: o banco do E2E é recriado, mas rodar
  // duas vezes contra um servidor já de pé esbarraria no e-mail repetido.
  const id = crypto.randomUUID().slice(0, 8)
  return {
    username: `aluno_${id}`,
    email: `aluno_${id}@ufrpe.br`,
    senha: 'Trilha-Boa-2026',
  }
}

test('cadastro, onboarding e chegada na home', async ({ page }) => {
  const novo = aluno()

  await page.goto('/cadastro')

  await page.getByLabel('Nome de usuário').fill(novo.username)
  await page.getByLabel('Email').fill(novo.email)
  await page.getByLabel('Senha', { exact: true }).fill(novo.senha)
  await page.getByLabel('Confirmar senha').fill(novo.senha)
  await page.getByLabel(/termos/i).check()
  await page.getByRole('button', { name: /criar conta/i }).click()

  // Passo 1: nível de experiência. Cada opção é um botão com `aria-pressed`,
  // e é ele que precisa ser clicado — o texto solto dentro dele não seleciona.
  await expect(page.getByText('Passo 1 de 3')).toBeVisible()
  await page.getByRole('button', { name: /^Baixo/ }).click()
  await page.getByRole('button', { name: 'Continuar' }).click()

  // Passo 2: tipo de trilha.
  await expect(page.getByText('Passo 2 de 3')).toBeVisible()
  await page.getByRole('button', { name: /^Guiada/ }).click()
  await page.getByRole('button', { name: 'Continuar' }).click()

  // Passo 3: dados acadêmicos. Na trilha guiada a grade curricular é
  // obrigatória: sem ela o "Continuar" mostra o erro e não segue. O arquivo vai
  // em memória para não precisar de fixture no repositório.
  await expect(page.getByText('Passo 3 de 3')).toBeVisible()
  await page.locator('#grade-curricular').setInputFiles({
    name: 'grade.pdf',
    mimeType: 'application/pdf',
    buffer: pdfComTexto(EMENTA_DE_TESTE),
  })

  // Instituição e curso pelo autocomplete, que vem do catálogo do seed. A busca
  // tolera o jeito que o aluno digita: sem acento e incompleto.
  await page.getByRole('combobox', { name: /universidade\/faculdade/i }).fill('rural pern')
  await page.getByRole('option', { name: /Rural de Pernambuco/ }).click()
  await page.getByRole('combobox', { name: /curso de graduação/i }).click()
  await page.getByRole('option', { name: /Sistemas de Informação/ }).click()

  const ementaEnviada = page.waitForResponse(
    (resposta) => resposta.url().endsWith('/api/v1/ementas') && resposta.status() === 202,
  )
  await page.getByRole('button', { name: 'Continuar' }).click()
  const { id: ementaId } = (await (await ementaEnviada).json()) as { id: number }

  // Na guiada, a ementa enviada leva à revisão dos assuntos (#38). Com o
  // provedor `Eco` a IA não devolve a leitura, e a tela mostra a falha com o
  // botão de tentar de novo: é a leitura de verdade, rodando no servidor.
  await expect(page).toHaveURL('/trilha-guiada/revisao')
  await expect(page.getByText('Não deu para ler os assuntos')).toBeVisible({ timeout: 15_000 })
  await expect(page.getByRole('button', { name: 'Tentar de novo' })).toBeVisible()

  // O que a tela mandou chegou ao perfil, com os nomes do catálogo.
  const login = await page.request.post(`${API}/auth/login`, {
    data: { email: novo.email, senha: novo.senha },
  })
  const { access_token } = (await login.json()) as { access_token: string }
  const perfil = await page.request.get(`${API}/usuarios/me`, {
    headers: { Authorization: `Bearer ${access_token}` },
  })
  expect(await perfil.json()).toMatchObject({
    instituicao: 'Universidade Federal Rural de Pernambuco',
    curso: 'Bacharelado em Sistemas de Informação',
    tipo_trilha: 'guiada',
  })

  // A leitura do PDF roda depois da resposta, no servidor de verdade: é o único
  // teste que a exercita com a sessão do banco que a API usa em produção.
  await expect
    .poll(async () => {
      const ementa = await page.request.get(`${API}/ementas/${ementaId}`, {
        headers: { Authorization: `Bearer ${access_token}` },
      })
      return ((await ementa.json()) as { status: string }).status
    })
    .toBe('processada')
})

test('cadastro com e-mail repetido mostra a mensagem da API', async ({ page, request }) => {
  const repetido = aluno()
  // Cria pela API para o teste medir só a reação do formulário.
  const criada = await request.post('http://127.0.0.1:8001/api/v1/auth/register', {
    data: { ...repetido, aceite_termos: true },
  })
  expect(criada.ok()).toBeTruthy()

  await page.goto('/cadastro')
  await page.getByLabel('Nome de usuário').fill(`${repetido.username}_2`)
  await page.getByLabel('Email').fill(repetido.email)
  await page.getByLabel('Senha', { exact: true }).fill(repetido.senha)
  await page.getByLabel('Confirmar senha').fill(repetido.senha)
  await page.getByLabel(/termos/i).check()
  await page.getByRole('button', { name: /criar conta/i }).click()

  await expect(page.getByRole('alert')).toContainText('e-mail')
  await expect(page).toHaveURL(/\/cadastro/)
})

test('login com senha errada não entra', async ({ page }) => {
  await page.goto('/login')

  await page.getByLabel('Email').fill('ninguem@ufrpe.br')
  await page.getByLabel('Senha').fill('Senha-Errada-2026')
  await page.getByRole('button', { name: 'Entrar' }).click()

  await expect(page.getByRole('alert')).toContainText(/incorreto/i)
  await expect(page).toHaveURL(/\/login/)
})

test('rota privada manda para o login', async ({ page }) => {
  await page.goto('/perfil')

  await expect(page).toHaveURL(/\/(login|boas-vindas)/)
})
