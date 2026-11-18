import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { ErroCampo } from '@/components/ui/erro-campo'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { BotoesLoginSocial } from '@/components/auth/BotoesLoginSocial'
import { OnboardingWizard } from '@/components/onboarding/OnboardingWizard'
import { useAuthStore } from '@/stores/useAuthStore'
import { temProgresso, useOnboardingStore } from '@/stores/useOnboardingStore'
import { mensagemDeErro } from '@/lib/erros'
import { cn } from '@/lib/utils'
import { solicitarRedefinicao } from '@/services/auth'
import {
  cadastroSchema,
  esqueciSenhaSchema,
  loginSchema,
  type CadastroFormValues,
  type EsqueciSenhaFormValues,
  type LoginFormValues,
} from '@/lib/validation/auth'
import logoAlgorise from '@/assets/images/logo-algorise.png'
import carrosselDuvidasAcademicas from '@/assets/images/carrossel-duvidas-academicas.png'
import carrosselPolvoBanheira from '@/assets/images/carrossel-polvo-banheira.png'
import carrosselEmentasFaculdade from '@/assets/images/carrossel-ementas-faculdade.png'

const slides = [
  {
    image: carrosselDuvidasAcademicas,
    text: 'Transformamos disciplinas em desafios práticos para acelerar seu aprendizado',
  },
  {
    image: carrosselPolvoBanheira,
    text: 'Aprenda programação do jeito da sua Faculdade!',
  },
  {
    image: carrosselEmentasFaculdade,
    text: 'Sua ementa, sua trilha. Criamos uma experiência de aprendizado personalizada para que você avance no seu ritmo e foque no que realmente importa. Você não se adapta ao aprendizado; o aprendizado se adapta a você.',
  },
]

type Modo = 'escolha' | 'entrar' | 'cadastro' | 'esqueci-senha' | 'onboarding'

function WelcomeCarousel() {
  const [[index, direction], setSlide] = useState([0, 0])

  useEffect(() => {
    const timer = setInterval(() => {
      setSlide(([current]) => [(current + 1) % slides.length, 1])
    }, 7000)
    return () => clearInterval(timer)
  }, [])

  function goTo(next: number) {
    const wrapped = (next + slides.length) % slides.length
    setSlide([wrapped, next > index ? 1 : -1])
  }

  const slide = slides[index]

  return (
    <div
      role="region"
      aria-roledescription="carrossel"
      aria-label="Sobre o Algorise"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === 'ArrowLeft') goTo(index - 1)
        if (event.key === 'ArrowRight') goTo(index + 1)
      }}
      className="flex w-full max-w-md flex-col items-center gap-4 text-center outline-none md:gap-8"
    >
      {/* Menor no celular: com a imagem cheia, "Entrar" e "Criar conta" ficavam abaixo da dobra. */}
      <div className="relative aspect-square w-full max-w-[13rem] md:max-w-sm">
        <AnimatePresence initial={false} custom={direction} mode="wait">
          <motion.img
            key={slide.image}
            src={slide.image}
            alt=""
            custom={direction}
            initial={{ opacity: 0, x: 40 * direction }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -40 * direction }}
            transition={{ duration: 0.4, ease: 'easeInOut' }}
            className="absolute inset-0 h-full w-full rounded-2xl object-contain"
          />
        </AnimatePresence>
      </div>

      <div className="flex min-h-[4.5rem] items-start justify-center px-2">
        <AnimatePresence mode="wait">
          <motion.p
            key={slide.text}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3 }}
            className="max-w-sm text-lg font-semibold"
          >
            {slide.text}
          </motion.p>
        </AnimatePresence>
      </div>

      {/* No celular, logo abaixo do texto: na posição absoluta, ficavam em cima dele. */}
      <div className="flex items-center justify-center gap-3 md:absolute md:inset-x-0 md:bottom-10 md:gap-2">
        {slides.map((s, i) => (
          <button
            key={s.text}
            type="button"
            aria-label={`Ir para slide ${i + 1}`}
            aria-current={i === index}
            onClick={() => goTo(i)}
            className={cn(
              // O ponto é de 8px, mas a área de toque vai a ~32px (o after:).
              'relative h-2 w-2 rounded-full transition-colors after:absolute after:-inset-3 after:content-[""]',
              i === index ? 'bg-primary-foreground' : 'bg-primary-foreground/40',
            )}
          />
        ))}
      </div>
    </div>
  )
}

function VoltarButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="mb-4 flex items-center gap-1 text-sm font-semibold text-muted-foreground transition-colors hover:text-foreground"
    >
      <ArrowLeft className="size-4" />
      Voltar
    </button>
  )
}

function EscolhaView({ onIrPara }: { onIrPara: (modo: Modo) => void }) {
  return (
    <div className="text-center">
      {/* No celular o carrossel logo acima já mostra a marca: a logo repetida empurrava os botões. */}
      <img src={logoAlgorise} alt="Algorise" className="mx-auto mb-6 hidden h-48 md:block" />

      <p className="text-lg text-foreground">
        <span className="font-bold">Descubra</span> um jeito mais{' '}
        <span className="font-bold">inteligente</span> de aprender{' '}
        <span className="font-bold">programação</span> com conteúdos adaptados ao{' '}
        <span className="font-bold">seu</span> curso.
      </p>

      <div className="mt-8 flex flex-col gap-3">
        <Button full size="lg" onClick={() => onIrPara('entrar')}>
          Entrar
        </Button>
        <Button variant="outline" full size="lg" onClick={() => onIrPara('cadastro')}>
          Criar conta
        </Button>
      </div>
    </div>
  )
}

function EntrarView({
  onVoltar,
  onIrPara,
  rascunho,
  onRascunhoChange,
}: {
  onVoltar: () => void
  onIrPara: (modo: Modo) => void
  rascunho: Partial<LoginFormValues>
  onRascunhoChange: (valores: Partial<LoginFormValues>) => void
}) {
  const entrar = useAuthStore((estado) => estado.entrar)
  const navigate = useNavigate()
  const [erro, setErro] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    control,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', senha: '', manterConectado: false, ...rascunho },
  })

  useEffect(() => {
    const subscription = watch((valores) => onRascunhoChange(valores))
    return () => subscription.unsubscribe()
  }, [watch, onRascunhoChange])

  async function onSubmit(dados: LoginFormValues) {
    setErro(null)
    try {
      await entrar(dados.email, dados.senha, dados.manterConectado)
      navigate('/')
    } catch (falha) {
      setErro(mensagemDeErro(falha))
    }
  }

  return (
    <div>
      <VoltarButton onClick={onVoltar} />

      <BotoesLoginSocial />

      <div className="my-6 flex items-center gap-3 text-sm text-muted-foreground">
        <span className="h-px flex-1 bg-border" />
        ou use seu e-mail
        <span className="h-px flex-1 bg-border" />
      </div>

      <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
        <div className="flex flex-col gap-1">
          <Label htmlFor="login-email">Email</Label>
          <Input
            id="login-email"
            type="email"
            placeholder="voce@exemplo.com"
            aria-invalid={!!errors.email}
            aria-describedby={errors.email ? 'login-email-erro' : undefined}
            {...register('email')}
          />
          <ErroCampo id="login-email-erro" mensagem={errors.email?.message} />
        </div>

        <div className="flex flex-col gap-1">
          <Label htmlFor="login-senha">Senha</Label>
          <Input
            id="login-senha"
            type="password"
            placeholder="Digite sua senha"
            aria-invalid={!!errors.senha}
            aria-describedby={errors.senha ? 'login-senha-erro' : undefined}
            {...register('senha')}
          />
          <ErroCampo id="login-senha-erro" mensagem={errors.senha?.message} />
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Controller
              control={control}
              name="manterConectado"
              render={({ field }) => (
                <Checkbox
                  id="login-manter-conectado"
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              )}
            />
            <Label htmlFor="login-manter-conectado" className="font-normal">
              Manter-se conectado
            </Label>
          </div>
          <button
            type="button"
            onClick={() => onIrPara('esqueci-senha')}
            className="text-sm font-semibold text-primary hover:underline"
          >
            Esqueceu a senha?
          </button>
        </div>

        {erro && (
          <p role="alert" className="text-sm font-semibold text-destructive">
            {erro}
          </p>
        )}

        <Button type="submit" full size="lg" disabled={isSubmitting}>
          {isSubmitting ? 'Entrando…' : 'Entrar'}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        Não tem uma conta?{' '}
        <button
          type="button"
          onClick={() => onIrPara('cadastro')}
          className="font-semibold text-primary hover:underline"
        >
          Criar conta
        </button>
      </p>
    </div>
  )
}

function CadastroView({
  onVoltar,
  onIrPara,
  rascunho,
  onRascunhoChange,
}: {
  onVoltar: () => void
  onIrPara: (modo: Modo) => void
  rascunho: Partial<CadastroFormValues>
  onRascunhoChange: (valores: Partial<CadastroFormValues>) => void
}) {
  const cadastrar = useAuthStore((estado) => estado.cadastrar)
  const [erro, setErro] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    control,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<CadastroFormValues>({
    resolver: zodResolver(cadastroSchema),
    defaultValues: {
      username: '',
      email: '',
      senha: '',
      confirmarSenha: '',
      termos: false,
      ...rascunho,
    },
  })

  useEffect(() => {
    const subscription = watch((valores) => onRascunhoChange(valores))
    return () => subscription.unsubscribe()
  }, [watch, onRascunhoChange])

  async function onSubmit(dados: CadastroFormValues) {
    setErro(null)
    try {
      await cadastrar({ username: dados.username, email: dados.email, senha: dados.senha })
      onIrPara('onboarding')
    } catch (falha) {
      setErro(mensagemDeErro(falha))
    }
  }

  return (
    <div>
      <VoltarButton onClick={onVoltar} />

      <BotoesLoginSocial />

      <div className="my-6 flex items-center gap-3 text-sm text-muted-foreground">
        <span className="h-px flex-1 bg-border" />
        ou use seu e-mail
        <span className="h-px flex-1 bg-border" />
      </div>

      <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
        <div className="flex flex-col gap-1">
          <Label htmlFor="cadastro-username">Nome de usuário</Label>
          <Input
            id="cadastro-username"
            placeholder="seu_usuario"
            aria-invalid={!!errors.username}
            aria-describedby={errors.username ? 'cadastro-username-erro' : undefined}
            {...register('username')}
          />
          <ErroCampo id="cadastro-username-erro" mensagem={errors.username?.message} />
        </div>

        <div className="flex flex-col gap-1">
          <Label htmlFor="cadastro-email">Email</Label>
          <Input
            id="cadastro-email"
            type="email"
            placeholder="voce@exemplo.com"
            aria-invalid={!!errors.email}
            aria-describedby={errors.email ? 'cadastro-email-erro' : undefined}
            {...register('email')}
          />
          <ErroCampo id="cadastro-email-erro" mensagem={errors.email?.message} />
        </div>

        <div className="flex flex-col gap-1">
          <Label htmlFor="cadastro-senha">Senha</Label>
          <Input
            id="cadastro-senha"
            type="password"
            placeholder="Crie uma senha"
            aria-invalid={!!errors.senha}
            aria-describedby={errors.senha ? 'cadastro-senha-erro' : undefined}
            {...register('senha')}
          />
          <ErroCampo id="cadastro-senha-erro" mensagem={errors.senha?.message} />
        </div>

        <div className="flex flex-col gap-1">
          <Label htmlFor="cadastro-confirmar-senha">Confirmar senha</Label>
          <Input
            id="cadastro-confirmar-senha"
            type="password"
            placeholder="Repita a senha"
            aria-invalid={!!errors.confirmarSenha}
            aria-describedby={errors.confirmarSenha ? 'cadastro-confirmar-senha-erro' : undefined}
            {...register('confirmarSenha')}
          />
          <ErroCampo id="cadastro-confirmar-senha-erro" mensagem={errors.confirmarSenha?.message} />
        </div>

        <div className="flex flex-col gap-1">
          <div className="flex items-start gap-2">
            <Controller
              control={control}
              name="termos"
              render={({ field }) => (
                <Checkbox
                  id="cadastro-termos"
                  ref={field.ref}
                  checked={field.value}
                  onCheckedChange={field.onChange}
                  aria-invalid={!!errors.termos}
                  aria-describedby={errors.termos ? 'cadastro-termos-erro' : undefined}
                  className="mt-0.5"
                />
              )}
            />
            <Label htmlFor="cadastro-termos" className="font-normal">
              Aceito os{' '}
              <Link to="/privacidade" className="font-semibold text-primary hover:underline">
                termos de uso e a política de privacidade
              </Link>
              .
            </Label>
          </div>
          <ErroCampo id="cadastro-termos-erro" mensagem={errors.termos?.message} />
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
        <button
          type="button"
          onClick={() => onIrPara('entrar')}
          className="font-semibold text-primary hover:underline"
        >
          Entrar
        </button>
      </p>
    </div>
  )
}

function EsqueciSenhaView({
  onVoltar,
  rascunho,
  onRascunhoChange,
}: {
  onVoltar: () => void
  rascunho: Partial<EsqueciSenhaFormValues>
  onRascunhoChange: (valores: Partial<EsqueciSenhaFormValues>) => void
}) {
  const [enviado, setEnviado] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<EsqueciSenhaFormValues>({
    resolver: zodResolver(esqueciSenhaSchema),
    defaultValues: { email: '', ...rascunho },
  })

  useEffect(() => {
    const subscription = watch((valores) => onRascunhoChange(valores))
    return () => subscription.unsubscribe()
  }, [watch, onRascunhoChange])

  async function onSubmit(dados: EsqueciSenhaFormValues) {
    setErro(null)
    try {
      await solicitarRedefinicao(dados.email)
      setEnviado(true)
    } catch (falha) {
      setErro(mensagemDeErro(falha))
    }
  }

  if (enviado) {
    return (
      <div className="text-center">
        <h1 className="mb-2 font-display text-xl font-bold text-foreground">Verifique seu email</h1>
        <p className="text-muted-foreground">
          Se esse email tiver uma conta, enviamos um link para redefinir a senha.
        </p>
        <button
          type="button"
          onClick={onVoltar}
          className="mt-6 font-semibold text-primary hover:underline"
        >
          Voltar para o login
        </button>
      </div>
    )
  }

  return (
    <div>
      <VoltarButton onClick={onVoltar} />

      <h1 className="mb-2 font-display text-xl font-bold text-foreground">Esqueceu a senha?</h1>
      <p className="mb-6 text-muted-foreground">
        Informe seu email e enviaremos um link para você criar uma nova senha.
      </p>

      <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
        <div className="flex flex-col gap-1">
          <Label htmlFor="esqueci-email">Email</Label>
          <Input
            id="esqueci-email"
            type="email"
            placeholder="voce@exemplo.com"
            aria-invalid={!!errors.email}
            aria-describedby={errors.email ? 'esqueci-email-erro' : undefined}
            {...register('email')}
          />
          <ErroCampo id="esqueci-email-erro" mensagem={errors.email?.message} />
        </div>

        {erro && (
          <p role="alert" className="text-sm font-semibold text-destructive">
            {erro}
          </p>
        )}

        <Button type="submit" full size="lg" disabled={isSubmitting}>
          {isSubmitting ? 'Enviando…' : 'Enviar link'}
        </Button>
      </form>
    </div>
  )
}

const MODOS: readonly Modo[] = ['escolha', 'entrar', 'cadastro', 'esqueci-senha', 'onboarding']

/**
 * O rascunho de um formulário, guardado na aba (`sessionStorage`).
 *
 * Abrir a política de privacidade no meio do cadastro desmonta esta página; ao
 * voltar, o aluno encontra o que já tinha digitado. Senha nunca é guardada.
 */
function useRascunho<T extends object>(chave: string) {
  const chaveCompleta = `algorise:rascunho:${chave}`
  const [rascunho, setRascunhoEmMemoria] = useState<Partial<T>>(() => {
    try {
      return JSON.parse(sessionStorage.getItem(chaveCompleta) ?? '{}') as Partial<T>
    } catch {
      return {}
    }
  })
  const setRascunho = useCallback(
    (valores: Partial<T>) => {
      setRascunhoEmMemoria(valores)
      const semSenha = Object.fromEntries(
        Object.entries(valores).filter(([campo]) => !/senha/i.test(campo)),
      )
      try {
        sessionStorage.setItem(chaveCompleta, JSON.stringify(semSenha))
      } catch {
        // Sem storage (aba anônima restrita): o rascunho fica só na memória.
      }
    },
    [chaveCompleta],
  )
  return [rascunho, setRascunho] as const
}

export function BoasVindasPage() {
  // A tela aberta (entrar, cadastro...) vai na URL: voltar da política de
  // privacidade, ou recarregar, devolve o aluno à mesma tela.
  const [parametros, setParametros] = useSearchParams()
  const tela = parametros.get('tela') as Modo | null
  const modo: Modo = tela && MODOS.includes(tela) ? tela : 'escolha'
  const setModo = useCallback(
    (novo: Modo) => setParametros(novo === 'escolha' ? {} : { tela: novo }, { replace: true }),
    [setParametros],
  )
  const [rascunhoEntrar, setRascunhoEntrar] = useRascunho<LoginFormValues>('entrar')
  const [rascunhoCadastro, setRascunhoCadastro] = useRascunho<CadastroFormValues>('cadastro')
  const [rascunhoEsqueci, setRascunhoEsqueci] = useRascunho<EsqueciSenhaFormValues>('esqueci')
  const usuarioId = useAuthStore((estado) => estado.usuario?.id)

  // Recarregou no meio do onboarding: assim que a sessão volta, volta também
  // para o wizard, que retoma o rascunho de onde parou.
  useEffect(() => {
    const { usuarioId: dono, rascunho } = useOnboardingStore.getState()
    if (usuarioId && usuarioId === dono && temProgresso(rascunho)) setModo('onboarding')
  }, [usuarioId, setModo])

  return (
    <div className="flex min-h-dvh flex-col md:flex-row">
      {/* No celular, o carrossel só na tela de escolha: nos formulários, o formulário vem primeiro. */}
      <div
        className={cn(
          'relative w-full flex-col items-center justify-center bg-primary px-6 py-8 text-primary-foreground md:flex md:w-1/2 md:px-8 md:py-12',
          modo === 'escolha' ? 'flex' : 'hidden',
        )}
      >
        <WelcomeCarousel />
      </div>

      <div className="flex w-full flex-1 flex-col items-center justify-center px-6 py-8 md:w-1/2 md:flex-none md:px-8 md:py-12">
        <div className="w-full max-w-sm">
          <AnimatePresence mode="wait">
            <motion.div
              key={modo}
              initial={{ opacity: 0, x: 16 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -16 }}
              transition={{ duration: 0.25 }}
            >
              {modo === 'escolha' && <EscolhaView onIrPara={setModo} />}
              {modo === 'entrar' && (
                <EntrarView
                  onVoltar={() => setModo('escolha')}
                  onIrPara={setModo}
                  rascunho={rascunhoEntrar}
                  onRascunhoChange={setRascunhoEntrar}
                />
              )}
              {modo === 'cadastro' && (
                <CadastroView
                  onVoltar={() => setModo('escolha')}
                  onIrPara={setModo}
                  rascunho={rascunhoCadastro}
                  onRascunhoChange={setRascunhoCadastro}
                />
              )}
              {modo === 'esqueci-senha' && (
                <EsqueciSenhaView
                  onVoltar={() => setModo('entrar')}
                  rascunho={rascunhoEsqueci}
                  onRascunhoChange={setRascunhoEsqueci}
                />
              )}
              {modo === 'onboarding' && (
                <OnboardingWizard onVoltarInicio={() => setModo('cadastro')} />
              )}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
