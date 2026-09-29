import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, type Variants } from 'framer-motion'
import {
  Accessibility,
  Info,
  KeyRound,
  LogOut,
  MessagesSquare,
  Monitor,
  Moon,
  Palette,
  Sun,
  Trash2,
  UserRound,
} from 'lucide-react'
import { OpcoesAcessibilidade } from '@/components/configuracoes/OpcoesAcessibilidade'
import { Opcao, Secao } from '@/components/configuracoes/Secao'
import { SecaoPrivacidade } from '@/components/configuracoes/SecaoPrivacidade'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { toast } from '@/components/ui/toaster'
import { useAuth } from '@/contexts/AuthContext'
import { useTheme, type PreferenciaTema } from '@/contexts/ThemeContext'
import { appVersion } from '@/lib/version'
import { cn } from '@/lib/utils'
import { solicitarRedefinicao } from '@/services/auth'
import { limparHistoricoChat } from '@/services/chat'
import type { Usuario } from '@/types/usuario'

const container: Variants = {
  oculto: {},
  visivel: { transition: { staggerChildren: 0.07 } },
}

const item: Variants = {
  oculto: { opacity: 0, y: 16 },
  visivel: { opacity: 1, y: 0, transition: { duration: 0.35, ease: 'easeOut' } },
}

const temas: { valor: PreferenciaTema; rotulo: string; icone: typeof Sun }[] = [
  { valor: 'claro', rotulo: 'Claro', icone: Sun },
  { valor: 'escuro', rotulo: 'Escuro', icone: Moon },
  { valor: 'sistema', rotulo: 'Sistema', icone: Monitor },
]

function SecaoConta({ usuario }: { usuario: Usuario }) {
  const { atualizarPerfil } = useAuth()
  const [nome, setNome] = useState(usuario.nome)
  const [salvandoNome, setSalvandoNome] = useState(false)
  const [enviandoLink, setEnviandoLink] = useState(false)
  const nomeMudou = nome.trim() !== usuario.nome && nome.trim().length >= 2

  async function salvarNome(event: FormEvent) {
    event.preventDefault()
    if (!nomeMudou) return
    setSalvandoNome(true)
    try {
      await atualizarPerfil({ nome: nome.trim() })
      toast.success('Nome atualizado')
    } catch (erro) {
      toast.error(erro instanceof Error ? erro.message : 'Não foi possível salvar.')
    } finally {
      setSalvandoNome(false)
    }
  }

  async function enviarLinkDeSenha() {
    setEnviandoLink(true)
    try {
      await solicitarRedefinicao(usuario.email)
      toast.success('Link enviado', {
        description: `Enviamos um link para ${usuario.email} para você criar uma nova senha.`,
      })
    } catch (erro) {
      toast.error(erro instanceof Error ? erro.message : 'Não foi possível enviar o link.')
    } finally {
      setEnviandoLink(false)
    }
  }

  return (
    <Secao icone={UserRound} titulo="Conta" descricao="Como você aparece no Algorise.">
      <form onSubmit={salvarNome} className="flex flex-col gap-2 pb-4">
        <label htmlFor="config-nome" className="font-semibold text-foreground">
          Nome de exibição
        </label>
        <div className="flex gap-2">
          <Input
            id="config-nome"
            value={nome}
            onChange={(event) => setNome(event.target.value)}
            maxLength={120}
          />
          <Button type="submit" disabled={!nomeMudou || salvandoNome} className="shrink-0">
            {salvandoNome ? 'Salvando…' : 'Salvar'}
          </Button>
        </div>
        <p className="text-sm text-muted-foreground">Aparece na Home, no ranking e no Perfil.</p>
      </form>

      <Opcao titulo="Nome de usuário">
        <span className="font-mono text-sm text-muted-foreground">
          {usuario.username ? `@${usuario.username}` : 'não definido'}
        </span>
      </Opcao>
      <Opcao titulo="E-mail">
        <span className="text-sm text-muted-foreground">{usuario.email}</span>
      </Opcao>
      <Opcao titulo="Senha" descricao="Enviamos um link para o seu e-mail para criar uma nova.">
        <Button variant="secondary" size="sm" onClick={enviarLinkDeSenha} disabled={enviandoLink}>
          <KeyRound className="!size-4" />
          {enviandoLink ? 'Enviando…' : 'Alterar senha'}
        </Button>
      </Opcao>
    </Secao>
  )
}

function SecaoAparencia() {
  const { preferencia, setPreferencia } = useTheme()

  return (
    <Secao icone={Palette} titulo="Aparência">
      {/* Um bloco só: a Secao põe divisória entre filhos diretos. */}
      <div>
        <div role="radiogroup" aria-label="Tema" className="grid grid-cols-3 gap-3">
          {temas.map((tema) => {
            const ativo = preferencia === tema.valor
            return (
              <motion.button
                key={tema.valor}
                type="button"
                role="radio"
                aria-checked={ativo}
                whileTap={{ scale: 0.96 }}
                onClick={() => setPreferencia(tema.valor)}
                className={cn(
                  'flex flex-col items-center gap-2 rounded-lg border-2 p-4 font-bold transition-colors',
                  ativo
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-border text-muted-foreground hover:border-primary/50 hover:text-foreground',
                )}
              >
                <tema.icone className="size-6" aria-hidden />
                {tema.rotulo}
              </motion.button>
            )
          })}
        </div>
        <p className="pt-3 text-sm text-muted-foreground">
          "Sistema" acompanha o modo claro/escuro do seu computador.
        </p>
      </div>
    </Secao>
  )
}

function SecaoDados() {
  const [aberto, setAberto] = useState(false)

  function limpar() {
    limparHistoricoChat()
    setAberto(false)
    toast.success('Histórico do chat apagado')
  }

  return (
    <Secao icone={MessagesSquare} titulo="Chat">
      <Opcao
        titulo="Histórico de conversas"
        descricao="As conversas ficam salvas só neste navegador."
      >
        <Dialog open={aberto} onOpenChange={setAberto}>
          <DialogTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="border-destructive text-destructive hover:bg-destructive/10"
            >
              <Trash2 className="!size-4" />
              Apagar histórico
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader className="text-left">
              <DialogTitle>Apagar todo o histórico?</DialogTitle>
              <DialogDescription>
                Todas as conversas e grupos do chat serão apagados deste navegador. Não dá para
                desfazer.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="ghost">Cancelar</Button>
              </DialogClose>
              <Button variant="destructive" onClick={limpar}>
                Apagar tudo
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </Opcao>
    </Secao>
  )
}

function SecaoSobre() {
  const { logout } = useAuth()
  const navigate = useNavigate()
  // Em desenvolvimento o build pode vir vazio ou fora do formato ISO.
  const dataBuild = appVersion.build ? new Date(appVersion.build) : null
  const build =
    dataBuild && !Number.isNaN(dataBuild.getTime())
      ? dataBuild.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
      : null

  return (
    <Secao icone={Info} titulo="Sobre e sessão">
      <Opcao titulo="Versão do app">
        <span className="font-mono text-sm text-muted-foreground">
          v{appVersion.versao} · {appVersion.commit}
          {build && ` · ${build}`}
        </span>
      </Opcao>
      <Opcao titulo="Sair da conta" descricao="Encerra a sessão neste navegador.">
        <Button
          variant="destructive"
          size="sm"
          onClick={() => {
            navigate('/boas-vindas')
            logout()
          }}
        >
          <LogOut className="!size-4" />
          Sair
        </Button>
      </Opcao>
    </Secao>
  )
}

export function ConfiguracoesPage() {
  const { usuario } = useAuth()
  if (!usuario) return null

  return (
    <motion.div
      variants={container}
      initial="oculto"
      animate="visivel"
      className="flex flex-col gap-6"
    >
      <motion.header variants={item}>
        <h1 className="font-display text-3xl font-bold text-foreground">Configurações</h1>
        <p className="text-muted-foreground">Preferências da sua conta e do aplicativo.</p>
      </motion.header>

      {/*
        Três colunas no desktop para caber sem rolar:
        conta + chat | aparência + sobre | acessibilidade + seus dados.
      */}
      <div className="grid items-start gap-6 lg:grid-cols-2 xl:grid-cols-3">
        <div className="flex flex-col gap-6">
          <motion.div variants={item}>
            <SecaoConta usuario={usuario} />
          </motion.div>
          <motion.div variants={item}>
            <SecaoDados />
          </motion.div>
        </div>
        <div className="flex flex-col gap-6">
          <motion.div variants={item}>
            <SecaoAparencia />
          </motion.div>
          <motion.div variants={item}>
            <SecaoSobre />
          </motion.div>
        </div>
        <div className="flex flex-col gap-6 lg:col-span-2 xl:col-span-1">
          <motion.div variants={item}>
            <Secao icone={Accessibility} titulo="Acessibilidade">
              <OpcoesAcessibilidade />
            </Secao>
          </motion.div>
          <motion.div variants={item}>
            <SecaoPrivacidade />
          </motion.div>
        </div>
      </div>
    </motion.div>
  )
}
