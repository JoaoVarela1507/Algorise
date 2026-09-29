import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { toast } from '@/components/ui/toaster'
import { useAuth } from '@/contexts/AuthContext'
import { mensagemDeErro } from '@/lib/erros'
import { USUARIO_TESTE } from '@/lib/loginTeste'
import { baixarMeusDados, excluirConta } from '@/services/auth'

// Mesmo texto que o backend exige (`CONFIRMACAO_DE_EXCLUSAO`).
const CONFIRMACAO = 'EXCLUIR'

export function ConfiguracoesPage() {
  const { usuario, logout } = useAuth()
  const navigate = useNavigate()
  const [baixando, setBaixando] = useState(false)
  const [dialogoAberto, setDialogoAberto] = useState(false)
  const [confirmacao, setConfirmacao] = useState('')
  const [senha, setSenha] = useState('')
  const [excluindo, setExcluindo] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  // O login de teste não tem conta na API: não há dado para baixar nem excluir.
  const sessaoDeTeste = usuario?.id === USUARIO_TESTE.id

  async function baixar() {
    setBaixando(true)
    try {
      await baixarMeusDados()
    } catch (falha) {
      toast.error(mensagemDeErro(falha))
    } finally {
      setBaixando(false)
    }
  }

  async function excluir() {
    setErro(null)
    setExcluindo(true)
    try {
      const data = await excluirConta({ confirmacao, senha })
      logout()
      navigate('/boas-vindas', { replace: true })
      toast('Sua conta foi desativada.', {
        description: `Os dados serão apagados em ${data.toLocaleDateString('pt-BR')}. Entrar de novo antes disso cancela a exclusão.`,
      })
    } catch (falha) {
      setErro(mensagemDeErro(falha))
    } finally {
      setExcluindo(false)
    }
  }

  return (
    <div className="flex max-w-2xl flex-col gap-8">
      <div>
        <h1 className="font-display text-2xl font-bold">Configurações</h1>
        <p className="text-muted-foreground">Preferências da conta e do aplicativo.</p>
      </div>

      <section className="flex flex-col gap-4 rounded-2xl border border-border p-6">
        <div>
          <h2 className="font-display text-lg font-bold">Seus dados</h2>
          <p className="text-sm text-muted-foreground">
            Veja o que guardamos na{' '}
            <Link to="/privacidade" className="font-semibold text-primary hover:underline">
              política de privacidade
            </Link>
            .
          </p>
        </div>

        {sessaoDeTeste && (
          <p className="rounded-lg border border-dashed border-border bg-muted/50 p-3 text-sm text-muted-foreground">
            Você está no login de teste, que não tem conta na API. Entre com uma conta de verdade
            para baixar ou excluir seus dados.
          </p>
        )}

        <div className="flex flex-wrap gap-3">
          <Button variant="outline" onClick={baixar} disabled={baixando || sessaoDeTeste}>
            {baixando ? 'Preparando…' : 'Baixar meus dados'}
          </Button>
          <Button
            variant="destructive"
            onClick={() => setDialogoAberto(true)}
            disabled={sessaoDeTeste}
          >
            Excluir conta
          </Button>
        </div>
      </section>

      <Dialog
        open={dialogoAberto}
        onOpenChange={(aberto) => {
          setDialogoAberto(aberto)
          if (!aberto) {
            setConfirmacao('')
            setSenha('')
            setErro(null)
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Excluir conta</DialogTitle>
            <DialogDescription>
              A conta é desativada agora e todos os seus dados são apagados de vez em 30 dias.
              Entrar de novo nesse prazo cancela a exclusão.
            </DialogDescription>
          </DialogHeader>

          <form
            className="flex flex-col gap-4"
            onSubmit={(evento) => {
              evento.preventDefault()
              void excluir()
            }}
          >
            <div className="flex flex-col gap-1">
              <Label htmlFor="excluir-confirmacao">
                Digite <span className="font-mono font-bold">{CONFIRMACAO}</span> para confirmar
              </Label>
              <Input
                id="excluir-confirmacao"
                autoComplete="off"
                value={confirmacao}
                onChange={(evento) => setConfirmacao(evento.target.value)}
              />
            </div>

            {usuario?.temSenha && (
              <div className="flex flex-col gap-1">
                <Label htmlFor="excluir-senha">Sua senha</Label>
                <Input
                  id="excluir-senha"
                  type="password"
                  autoComplete="current-password"
                  value={senha}
                  onChange={(evento) => setSenha(evento.target.value)}
                />
              </div>
            )}

            {erro && (
              <p role="alert" className="text-sm font-semibold text-destructive">
                {erro}
              </p>
            )}

            <DialogFooter>
              <Button type="button" variant="ghost" onClick={() => setDialogoAberto(false)}>
                Cancelar
              </Button>
              <Button
                type="submit"
                variant="destructive"
                disabled={
                  excluindo ||
                  confirmacao.trim().toUpperCase() !== CONFIRMACAO ||
                  (usuario?.temSenha && !senha)
                }
              >
                {excluindo ? 'Excluindo…' : 'Excluir minha conta'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
