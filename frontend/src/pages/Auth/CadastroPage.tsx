import { Link, useNavigate } from 'react-router-dom'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { GithubIcon, GoogleIcon } from '@/components/icons/OAuthIcons'
import { useAuth } from '@/contexts/AuthContext'
import { cadastroSchema, type CadastroFormValues } from '@/lib/validation/auth'

export function CadastroPage() {
  const { login } = useAuth()
  const navigate = useNavigate()

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
    await new Promise((resolve) => setTimeout(resolve, 500))

    login({
      id: 'novo-usuario',
      nome: dados.username,
      email: dados.email,
      nivelExperiencia: 'baixo',
      tipoTrilha: 'guiada',
      xp: 0,
      streakDias: 0,
    })
    navigate('/onboarding')
  }

  return (
    <div>
      <div className="flex flex-col gap-3">
        <Button type="button" variant="secondary" full size="lg">
          <GithubIcon />
          Continuar com GitHub
        </Button>
        <Button type="button" variant="secondary" full size="lg">
          <GoogleIcon />
          Continuar com Google
        </Button>
      </div>

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
            {...register('username')}
          />
          {errors.username && (
            <p role="alert" className="text-sm text-destructive">
              {errors.username.message}
            </p>
          )}
        </div>

        <div className="flex flex-col gap-1">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            placeholder="voce@exemplo.com"
            aria-invalid={!!errors.email}
            {...register('email')}
          />
          {errors.email && (
            <p role="alert" className="text-sm text-destructive">
              {errors.email.message}
            </p>
          )}
        </div>

        <div className="flex flex-col gap-1">
          <Label htmlFor="senha">Senha</Label>
          <Input
            id="senha"
            type="password"
            placeholder="Crie uma senha"
            aria-invalid={!!errors.senha}
            {...register('senha')}
          />
          {errors.senha && (
            <p role="alert" className="text-sm text-destructive">
              {errors.senha.message}
            </p>
          )}
        </div>

        <div className="flex flex-col gap-1">
          <Label htmlFor="confirmarSenha">Confirmar senha</Label>
          <Input
            id="confirmarSenha"
            type="password"
            placeholder="Repita a senha"
            aria-invalid={!!errors.confirmarSenha}
            {...register('confirmarSenha')}
          />
          {errors.confirmarSenha && (
            <p role="alert" className="text-sm text-destructive">
              {errors.confirmarSenha.message}
            </p>
          )}
        </div>

        <div className="flex flex-col gap-1">
          <div className="flex items-start gap-2">
            <Controller
              control={control}
              name="termos"
              render={({ field }) => (
                <Checkbox
                  id="termos"
                  checked={field.value}
                  onCheckedChange={field.onChange}
                  className="mt-0.5"
                />
              )}
            />
            <Label htmlFor="termos" className="font-normal">
              Aceito os termos de uso e a política de privacidade.
            </Label>
          </div>
          {errors.termos && (
            <p role="alert" className="text-sm text-destructive">
              {errors.termos.message}
            </p>
          )}
        </div>

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
