import { z } from 'zod'

const emailSchema = z.string().min(1, 'Informe seu email.').email('Email inválido.')
const senhaSchema = z.string().min(8, 'A senha precisa ter pelo menos 8 caracteres.')

export const loginSchema = z.object({
  email: emailSchema,
  senha: senhaSchema,
  manterConectado: z.boolean(),
})

export type LoginFormValues = z.infer<typeof loginSchema>

export const cadastroSchema = z
  .object({
    username: z
      .string()
      .min(3, 'O nome de usuário precisa ter pelo menos 3 caracteres.')
      .regex(/^[a-zA-Z0-9_]+$/, 'Use apenas letras, números e underline.'),
    email: emailSchema,
    senha: senhaSchema,
    confirmarSenha: z.string(),
    termos: z.boolean().refine((v) => v, 'Você precisa aceitar os termos de uso.'),
  })
  .refine((data) => data.senha === data.confirmarSenha, {
    message: 'As senhas não coincidem.',
    path: ['confirmarSenha'],
  })

export type CadastroFormValues = z.infer<typeof cadastroSchema>

export const esqueciSenhaSchema = z.object({
  email: emailSchema,
})

export type EsqueciSenhaFormValues = z.infer<typeof esqueciSenhaSchema>

export const redefinirSenhaSchema = z
  .object({
    senha: senhaSchema,
    confirmarSenha: z.string(),
  })
  .refine((data) => data.senha === data.confirmarSenha, {
    message: 'As senhas não coincidem.',
    path: ['confirmarSenha'],
  })

export type RedefinirSenhaFormValues = z.infer<typeof redefinirSenhaSchema>
