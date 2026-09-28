import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { GithubIcon, GoogleIcon } from '@/components/icons/OAuthIcons'
import { useAuth } from '@/contexts/AuthContext'
import { loginSchema, type LoginFormValues } from '@/lib/validation/auth'

// Login de teste enquanto a #10 (JWT/OAuth2 no backend) não é mergeada.
const LOGIN_TESTE = { email: 'teste@email.com', senha: '12345678' }

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [erroCredenciais, setErroCredenciais] = useState(false)

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', senha: '', manterConectado: false },
  })

  async function onSubmit(dados: LoginFormValues) {
    setErroCredenciais(false)
    await new Promise((resolve) => setTimeout(resolve, 500))

    if (dados.email !== LOGIN_TESTE.email || dados.senha !== LOGIN_TESTE.senha) {
      setErroCredenciais(true)
      return
    }

    login({
      id: 'usuario-teste',
      nome: 'Usuário Teste',
      email: LOGIN_TESTE.email,
      nivelExperiencia: 'medio',
      tipoTrilha: 'guiada',
      xp: 0,
      streakDias: 0,
    })
    navigate('/')
  }

  return (
    <div>
      <p className="mb-6 text-center text-foreground">
        <span className="font-bold">Descubra</span> um jeito mais{' '}
        <span className="font-bold">inteligente</span> de aprender{' '}
        <span className="font-bold">programação</span>.
      </p>

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
            placeholder="Digite sua senha"
            aria-invalid={!!errors.senha}
            {...register('senha')}
          />
          {errors.senha && (
            <p role="alert" className="text-sm text-destructive">
              {errors.senha.message}
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Controller
              control={control}
              name="manterConectado"
              render={({ field }) => (
                <Checkbox
                  id="manterConectado"
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              )}
            />
            <Label htmlFor="manterConectado" className="font-normal">
              Manter-se conectado
            </Label>
          </div>
          <Link to="/esqueci-senha" className="text-sm font-semibold text-primary hover:underline">
            Esqueceu a senha?
          </Link>
        </div>

        {erroCredenciais && (
          <p role="alert" className="text-sm font-semibold text-destructive">
            Email ou senha incorretos.
          </p>
        )}

        <Button type="submit" full size="lg" disabled={isSubmitting}>
          {isSubmitting ? 'Entrando…' : 'Entrar'}
        </Button>
      </form>

      <p className="mt-4 rounded-lg border border-dashed border-border bg-muted/50 p-3 text-center text-xs text-muted-foreground">
        Login de teste (dev): <span className="font-mono">{LOGIN_TESTE.email}</span> /{' '}
        <span className="font-mono">{LOGIN_TESTE.senha}</span>
      </p>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        Não tem uma conta?{' '}
        <Link to="/cadastro" className="font-semibold text-primary hover:underline">
          Criar conta
        </Link>
      </p>
    </div>
  )
}
