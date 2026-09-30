import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { GithubIcon, GoogleIcon } from '@/components/icons/OAuthIcons'
import { toast } from '@/components/ui/toaster'
import { iniciarLoginSocial, type Provedor } from '@/services/auth'

/** "Continuar com GitHub/Google" das telas 5 e 6. */
export function BotoesLoginSocial() {
  const [indo, setIndo] = useState<Provedor | null>(null)

  async function continuar(provedor: Provedor) {
    setIndo(provedor)
    try {
      // Em caso de sucesso o navegador sai da página; só volta aqui no erro.
      await iniciarLoginSocial(provedor)
    } catch (erro) {
      toast.error(erro instanceof Error ? erro.message : 'Não foi possível continuar.')
      setIndo(null)
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <Button
        type="button"
        variant="secondary"
        full
        size="lg"
        disabled={indo !== null}
        onClick={() => continuar('github')}
      >
        <GithubIcon />
        {indo === 'github' ? 'Redirecionando…' : 'Continuar com GitHub'}
      </Button>
      <Button
        type="button"
        variant="secondary"
        full
        size="lg"
        disabled={indo !== null}
        onClick={() => continuar('google')}
      >
        <GoogleIcon />
        {indo === 'google' ? 'Redirecionando…' : 'Continuar com Google'}
      </Button>
      {/* A conta criada pelo provedor não passa pelo checkbox do cadastro: o
          aceite é este aviso, e o backend o registra (LGPD). */}
      <p className="text-center text-xs text-muted-foreground">
        Ao continuar com GitHub ou Google, você aceita os{' '}
        <a
          href="/privacidade"
          target="_blank"
          rel="noreferrer"
          className="font-semibold text-primary hover:underline"
        >
          termos de uso e a política de privacidade
        </a>
        .
      </p>
    </div>
  )
}
