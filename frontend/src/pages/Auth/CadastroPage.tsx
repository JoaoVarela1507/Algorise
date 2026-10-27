import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { ErroCampo } from '@/components/ui/erro-campo'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { BotoesLoginSocial } from '@/components/auth/BotoesLoginSocial'
import { useAuthStore } from '@/stores/useAuthStore'
import { mensagemDeErro } from '@/lib/erros'
import { cadastroSchema, type CadastroFormValues } from '@/lib/validation/auth'

export function CadastroPage() {
  const cadastrar = useAuthStore((estado) => estado.cadastrar)
  const navigate = useNavigate()
  const [erro, setErro] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<CadastroFormValues>({
    resolver: zodResolver(cadastroSchema),
    defaultValues: { username: '', email: '', senha: '', confirmarSenha: '', termos: false },
  })

  async function onSubmit(dados: CadastroFormValues) {
    setErro(null)
    try {
      await cadastrar({ username: dados.username, email: dados.email, senha: dados.senha })
      navigate('/onboarding')
    } catch (falha) {
      setErro(mensagemDeErro(falha))
    }
  }

  return (
    <div>
      <BotoesLoginSocial />

      <div className="my-6 flex items-center gap-3 text-sm text-muted-foreground">
        <span className="h-px flex-1 bg-border" />
        ou use seu e-mail
        <span className="h-px flex-1 bg-border" />
      </div>

      <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
        <div className="flex flex-col gap-1">
          <Label htmlFor="username">Nome de usuário</Label>
          <Input
            id="username"
            placeholder="seu_usuario"
            aria-invalid={!!errors.username}
            aria-describedby={errors.username ? 'username-erro' : undefined}
            {...register('username')}
          />
          <ErroCampo id="username-erro" mensagem={errors.username?.message} />
        </div>

        <div className="flex flex-col gap-1">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            placeholder="voce@exemplo.com"
            aria-invalid={!!errors.email}
            aria-describedby={errors.email ? 'email-erro' : undefined}
            {...register('email')}
          />
          <ErroCampo id="email-erro" mensagem={errors.email?.message} />
        </div>

        <div className="flex flex-col gap-1">
          <Label htmlFor="senha">Senha</Label>
          <Input
            id="senha"
            type="password"
            placeholder="Crie uma senha"
            aria-invalid={!!errors.senha}
            aria-describedby={errors.senha ? 'senha-erro' : undefined}
            {...register('senha')}
          />
          <ErroCampo id="senha-erro" mensagem={errors.senha?.message} />
        </div>

        <div className="flex flex-col gap-1">
          <Label htmlFor="confirmarSenha">Confirmar senha</Label>
          <Input
            id="confirmarSenha"
            type="password"
            placeholder="Repita a senha"
            aria-invalid={!!errors.confirmarSenha}
            aria-describedby={errors.confirmarSenha ? 'confirmarSenha-erro' : undefined}
            {...register('confirmarSenha')}
          />
          <ErroCampo id="confirmarSenha-erro" mensagem={errors.confirmarSenha?.message} />
        </div>

        <div className="flex flex-col gap-1">
          <div className="flex items-start gap-2">
            <Controller
              control={control}
              name="termos"
              render={({ field }) => (
                <Checkbox
                  id="termos"
                  ref={field.ref}
                  checked={field.value}
                  onCheckedChange={field.onChange}
                  aria-invalid={!!errors.termos}
                  aria-describedby={errors.termos ? 'termos-erro' : undefined}
                  className="mt-0.5"
                />
              )}
            />
            <Label htmlFor="termos" className="font-normal">
              Aceito os{' '}
              <a
                href="/privacidade"
                target="_blank"
                rel="noreferrer"
                className="font-semibold text-primary hover:underline"
              >
                termos de uso e a política de privacidade
              </a>
              .
            </Label>
          </div>
          <ErroCampo id="termos-erro" mensagem={errors.termos?.message} />
        </div>

        {erro && (
          <p role="alert" className="text-sm font-semibold text-destructive">
            {erro}
          </p>
        )}

        <Button type="submit" full size="lg" disabled={isSubmitting}>
          {isSubmitting ? 'Criando conta…' : 'Criar conta'}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        Já tem uma conta?{' '}
        <Link to="/login" className="font-semibold text-primary hover:underline">
          Entrar
        </Link>
      </p>
    </div>
  )
}
