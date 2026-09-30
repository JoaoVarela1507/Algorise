import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { mensagemDeErro } from '@/lib/erros'
import { redefinirSenhaSchema, type RedefinirSenhaFormValues } from '@/lib/validation/auth'
import { redefinirSenha } from '@/services/auth'

/** Destino do link de "Esqueceu a senha?": `/redefinir-senha?token=...`. */
export function RedefinirSenhaPage() {
  const [parametros] = useSearchParams()
  const token = parametros.get('token')
  const [concluido, setConcluido] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RedefinirSenhaFormValues>({
    resolver: zodResolver(redefinirSenhaSchema),
    defaultValues: { senha: '', confirmarSenha: '' },
  })

  async function onSubmit(dados: RedefinirSenhaFormValues) {
    if (!token) return
    setErro(null)
    try {
      await redefinirSenha(token, dados.senha)
      setConcluido(true)
    } catch (falha) {
      setErro(mensagemDeErro(falha))
    }
  }

  if (!token || concluido) {
    return (
      <div className="text-center">
        <h1 className="mb-2 font-display text-xl font-bold text-foreground">
          {concluido ? 'Senha alterada' : 'Link inválido'}
        </h1>
        <p className="text-muted-foreground">
          {concluido
            ? 'Entre com a senha nova. Por segurança, as outras sessões abertas foram encerradas.'
            : 'Este link não tem o código de redefinição. Peça um novo em "Esqueceu a senha?".'}
        </p>
        <Link
          to="/boas-vindas"
          className="mt-6 inline-block font-semibold text-primary hover:underline"
        >
          Ir para o login
        </Link>
      </div>
    )
  }

  return (
    <div>
      <h1 className="mb-2 font-display text-xl font-bold text-foreground">Criar nova senha</h1>
      <p className="mb-6 text-muted-foreground">Escolha uma senha com pelo menos 8 caracteres.</p>

      <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
        <div className="flex flex-col gap-1">
          <Label htmlFor="nova-senha">Nova senha</Label>
          <Input
            id="nova-senha"
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
          <Label htmlFor="nova-senha-confirmar">Confirmar senha</Label>
          <Input
            id="nova-senha-confirmar"
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

        {erro && (
          <p role="alert" className="text-sm font-semibold text-destructive">
            {erro}
          </p>
        )}

        <Button type="submit" full size="lg" disabled={isSubmitting}>
          {isSubmitting ? 'Salvando…' : 'Salvar nova senha'}
        </Button>
      </form>
    </div>
  )
}
