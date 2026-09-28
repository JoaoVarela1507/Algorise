import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { esqueciSenhaSchema, type EsqueciSenhaFormValues } from '@/lib/validation/auth'

export function EsqueciSenhaPage() {
  const [enviado, setEnviado] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<EsqueciSenhaFormValues>({
    resolver: zodResolver(esqueciSenhaSchema),
    defaultValues: { email: '' },
  })

  async function onSubmit() {
    await new Promise((resolve) => setTimeout(resolve, 500))
    setEnviado(true)
  }

  if (enviado) {
    return (
      <div className="text-center">
        <h1 className="mb-2 font-display text-xl font-bold text-foreground">Verifique seu email</h1>
        <p className="text-muted-foreground">
          Se esse email tiver uma conta, enviamos um link para redefinir a senha.
        </p>
        <Link to="/login" className="mt-6 inline-block font-semibold text-primary hover:underline">
          Voltar para o login
        </Link>
      </div>
    )
  }

  return (
    <div>
      <h1 className="mb-2 font-display text-xl font-bold text-foreground">Esqueceu a senha?</h1>
      <p className="mb-6 text-muted-foreground">
        Informe seu email e enviaremos um link para você criar uma nova senha.
      </p>

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

        <Button type="submit" full size="lg" disabled={isSubmitting}>
          {isSubmitting ? 'Enviando…' : 'Enviar link'}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        Lembrou a senha?{' '}
        <Link to="/login" className="font-semibold text-primary hover:underline">
          Entrar
        </Link>
      </p>
    </div>
  )
}
