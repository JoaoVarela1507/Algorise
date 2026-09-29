import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from '@/components/ui/toaster'
import { useAuth } from '@/contexts/AuthContext'
import { mensagemDeErro } from '@/lib/erros'

// Códigos que o backend manda em `?erro=` (ver `app/api/routes/oauth.py`).
const MENSAGENS: Record<string, string> = {
  falha_no_login: 'O login não foi concluído. Tente de novo.',
  email_nao_verificado:
    'Sua conta no provedor não tem um e-mail verificado. Verifique o e-mail lá e tente de novo.',
  sessao_indisponivel: 'Não foi possível abrir a sessão agora. Tente de novo em instantes.',
}

/**
 * Volta do GitHub/Google. Sucesso chega com os tokens no fragmento
 * (`#access_token=...&refresh_token=...`), erro com `?erro=<código>`.
 */
export function OAuthCallbackPage() {
  const { concluirLoginSocial } = useAuth()
  const navigate = useNavigate()
  const [erro, setErro] = useState<string | null>(null)
  // O StrictMode monta duas vezes em desenvolvimento, e o fragmento já foi
  // apagado na primeira: sem isso a segunda veria "sem token" e mostraria erro.
  const processado = useRef(false)

  useEffect(() => {
    if (processado.current) return
    processado.current = true

    const fragmento = new URLSearchParams(window.location.hash.slice(1))
    const codigoErro = new URLSearchParams(window.location.search).get('erro')
    const access_token = fragmento.get('access_token')
    const refresh_token = fragmento.get('refresh_token')
    const aviso = fragmento.get('aviso')

    // Tira os tokens da barra de endereço e do histórico do navegador.
    window.history.replaceState(null, '', window.location.pathname)

    if (codigoErro || !access_token || !refresh_token) {
      setErro(MENSAGENS[codigoErro ?? ''] ?? MENSAGENS.falha_no_login)
      return
    }

    concluirLoginSocial({ access_token, refresh_token })
      .then(() => {
        if (aviso === 'exclusao_cancelada') {
          toast('A exclusão da sua conta foi cancelada porque você entrou de novo.')
        }
        navigate('/', { replace: true })
      })
      .catch((falha: unknown) => setErro(mensagemDeErro(falha)))
  }, [concluirLoginSocial, navigate])

  if (!erro) {
    return <p className="text-center text-muted-foreground">Entrando…</p>
  }

  return (
    <div className="text-center">
      <h1 className="mb-2 font-display text-xl font-bold text-foreground">Não deu para entrar</h1>
      <p className="text-muted-foreground">{erro}</p>
      <Link
        to="/boas-vindas"
        className="mt-6 inline-block font-semibold text-primary hover:underline"
      >
        Voltar para o login
      </Link>
    </div>
  )
}
