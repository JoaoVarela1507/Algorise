import { expect, type APIRequestContext, type Page } from '@playwright/test'

/** Onde a API sobe no E2E (ver `webServer` no playwright.config.ts). */
export const API = 'http://127.0.0.1:8001/api/v1'

export interface Conta {
  username: string
  email: string
  senha: string
}

/**
 * Cria a conta pela API, e não pela tela.
 *
 * Passar pelo formulário de cadastro em todo teste transformaria qualquer
 * mudança nele em falha de todos os outros. O cadastro pela tela tem o teste
 * dele em `cadastro.spec.ts`.
 */
export async function criarConta(request: APIRequestContext): Promise<Conta> {
  // `randomUUID` e não `Math.random`: além de não repetir entre execuções
  // paralelas, evita o alerta de aleatoriedade fraca do CodeQL.
  const id = crypto.randomUUID().slice(0, 8)
  const conta: Conta = {
    username: `aluno_${id}`,
    email: `aluno_${id}@ufrpe.br`,
    senha: 'Trilha-Boa-2026',
  }

  const resposta = await request.post(`${API}/auth/register`, {
    data: { ...conta, aceite_termos: true },
  })
  expect(resposta.ok(), await resposta.text()).toBeTruthy()

  return conta
}

/** Entra pela tela de login e espera a home. */
export async function entrar(page: Page, conta: Conta): Promise<void> {
  await page.goto('/login')
  await page.getByLabel('Email').fill(conta.email)
  await page.getByLabel('Senha').fill(conta.senha)
  await page.getByRole('button', { name: 'Entrar' }).click()
  await expect(page).toHaveURL('/')
}

/**
 * Um access token da conta, pedido direto à API.
 *
 * O app guarda o access token em memória (só o refresh vai para o navegador),
 * então o teste não tem como pescá-lo da página — e nem deveria: pedir um novo
 * é mais simples e não depende de detalhe interno do frontend.
 */
export async function cabecalhoDe(request: APIRequestContext, conta: Conta) {
  const resposta = await request.post(`${API}/auth/login`, {
    data: { email: conta.email, senha: conta.senha },
  })
  expect(resposta.ok(), await resposta.text()).toBeTruthy()

  const { access_token } = (await resposta.json()) as { access_token: string }
  return { Authorization: `Bearer ${access_token}` }
}

/**
 * PDF mínimo com texto selecionável, montado em memória.
 *
 * O backend extrai o texto da ementa, então um arquivo que só começa com
 * `%PDF-` passa no upload mas falha na leitura. Para o caminho feliz, precisa
 * ser um PDF de verdade.
 */
export function pdfComTexto(linhas: string[]): Buffer {
  const texto = linhas.map((linha) => `(${linha}) Tj 0 -16 Td`).join(' ')
  const conteudo = `BT /F1 12 Tf 72 720 Td ${texto} ET`
  const objetos = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] ' +
      '/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>',
    `<< /Length ${conteudo.length} >>\nstream\n${conteudo}\nendstream`,
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
  ]

  let pdf = '%PDF-1.4\n'
  const deslocamentos = objetos.map((corpo, i) => {
    const inicio = pdf.length
    pdf += `${i + 1} 0 obj\n${corpo}\nendobj\n`
    return inicio
  })
  const xref = pdf.length
  pdf += `xref\n0 ${objetos.length + 1}\n0000000000 65535 f \n`
  pdf += deslocamentos.map((d) => `${String(d).padStart(10, '0')} 00000 n \n`).join('')
  pdf += `trailer\n<< /Size ${objetos.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`
  return Buffer.from(pdf, 'latin1')
}

export const EMENTA_DE_TESTE = [
  'Introducao a Programacao - 60 horas',
  'Conteudo programatico: variaveis, condicionais, lacos e funcoes.',
]
