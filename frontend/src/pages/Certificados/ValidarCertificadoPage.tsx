import { useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { BadgeCheck, SearchX } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Carregando, ErroAoCarregar } from '@/components/ui/estados'
import { Input } from '@/components/ui/input'
import { useValidacao } from '@/hooks/useCertificados'
import { ApiError } from '@/services/api'

/**
 * Validação pública de certificado (#32): sem login, para quem recebeu o PDF
 * conferir o código impresso nele. Mostra só o que o certificado diz.
 */
export function ValidarCertificadoPage() {
  const { codigo } = useParams()
  const navigate = useNavigate()
  const [digitado, setDigitado] = useState(codigo ?? '')
  const validacao = useValidacao(codigo)

  function conferir(evento: FormEvent) {
    evento.preventDefault()
    if (digitado.trim()) navigate(`/validar/${encodeURIComponent(digitado.trim())}`)
  }

  let resultado = null
  if (codigo && validacao.isPending) {
    resultado = <Carregando rotulo="Conferindo o certificado…" />
  } else if (codigo && validacao.isError) {
    resultado =
      validacao.error instanceof ApiError && validacao.error.status === 404 ? (
        <div role="alert" className="flex flex-col items-center gap-2 py-8 text-center">
          <SearchX className="size-10 text-destructive" aria-hidden />
          <p className="font-display text-lg font-bold text-foreground">
            Nenhum certificado com esse código
          </p>
          <p className="text-sm text-muted-foreground">Confira se o código foi digitado certo.</p>
        </div>
      ) : (
        <ErroAoCarregar erro={validacao.error} aoTentarDeNovo={() => void validacao.refetch()} />
      )
  } else if (validacao.data) {
    const dados = validacao.data
    const emitido = dados.emitido_em ? new Date(dados.emitido_em).toLocaleDateString('pt-BR') : null
    resultado = (
      <section
        aria-label="Certificado válido"
        className="flex flex-col gap-3 rounded-lg border border-success/40 bg-success/10 p-6"
      >
        <p className="flex items-center gap-2 font-display text-lg font-bold text-success">
          <BadgeCheck className="size-6" aria-hidden />
          Certificado válido
        </p>
        <dl className="grid gap-2 text-sm sm:grid-cols-[auto_1fr] sm:gap-x-6">
          <dt className="font-semibold text-muted-foreground">Aluno</dt>
          <dd className="text-foreground">{dados.nome_aluno}</dd>
          <dt className="font-semibold text-muted-foreground">Trilha</dt>
          <dd className="text-foreground">{dados.nome_trilha}</dd>
          <dt className="font-semibold text-muted-foreground">Disciplina</dt>
          <dd className="text-foreground">{dados.disciplina}</dd>
          {dados.carga_horaria && (
            <>
              <dt className="font-semibold text-muted-foreground">Carga horária</dt>
              <dd className="text-foreground">{dados.carga_horaria} horas</dd>
            </>
          )}
          <dt className="font-semibold text-muted-foreground">Emitido por</dt>
          <dd className="text-foreground">
            {dados.parceiro}
            {emitido ? `, em ${emitido}` : ''}
          </dd>
          <dt className="font-semibold text-muted-foreground">Código</dt>
          <dd className="font-mono text-foreground">{dados.codigo}</dd>
        </dl>
      </section>
    )
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-xl flex-col gap-6 px-4 py-12">
      <header>
        <h1 className="font-display text-3xl font-bold text-foreground">Validar certificado</h1>
        <p className="text-muted-foreground">
          Digite o código impresso no certificado do Algorise.
        </p>
      </header>
      <form onSubmit={conferir} className="flex gap-2">
        <Input
          value={digitado}
          onChange={(evento) => setDigitado(evento.target.value)}
          placeholder="ALG-XXXX-XXXX"
          aria-label="Código do certificado"
          maxLength={40}
        />
        <Button type="submit">Conferir</Button>
      </form>
      {resultado}
    </main>
  )
}
