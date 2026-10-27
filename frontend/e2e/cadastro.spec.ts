import { expect, test } from '@playwright/test'

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
  // obrigatória — sem ela o "Continuar" fica desabilitado. O arquivo vai em
  // memória para não precisar de fixture no repositório.
  await expect(page.getByText('Passo 3 de 3')).toBeVisible()
  await page.locator('#grade-curricular').setInputFiles({
    name: 'grade.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.from('%PDF-1.4 grade de teste'),
  })
  await page.getByLabel(/universidade\/faculdade/i).fill('UFRPE')
  await page.getByLabel(/curso de graduação/i).fill('Ciência da Computação')
  await page.getByRole('button', { name: 'Continuar' }).click()

  await expect(page).toHaveURL('/')
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
