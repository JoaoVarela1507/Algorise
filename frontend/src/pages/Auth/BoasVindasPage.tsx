import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { GithubIcon, GoogleIcon } from '@/components/icons/OAuthIcons'
import { OnboardingWizard, type RascunhoOnboarding } from '@/components/onboarding/OnboardingWizard'
import { useAuth } from '@/contexts/AuthContext'
import { cn } from '@/lib/utils'
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

// Login de teste enquanto a #10 (JWT/OAuth2 no backend) não é mergeada.
const LOGIN_TESTE = { email: 'teste@email.com', senha: '12345678' }

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
      className="flex w-full max-w-md flex-col items-center gap-8 text-center outline-none"
    >
      <div className="relative aspect-square w-full max-w-sm">
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

      <div className="absolute inset-x-0 bottom-10 flex items-center justify-center gap-2">
        {slides.map((s, i) => (
          <button
            key={s.text}
            type="button"
            aria-label={`Ir para slide ${i + 1}`}
            aria-current={i === index}
            onClick={() => goTo(i)}
            className={cn(
              'h-2 w-2 rounded-full transition-colors',
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
      <img src={logoAlgorise} alt="Algorise" className="mx-auto mb-6 h-48" />

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
  const { login } = useAuth()
  const navigate = useNavigate()
  const [erroCredenciais, setErroCredenciais] = useState(false)

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
      <VoltarButton onClick={onVoltar} />

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
          <Label htmlFor="login-email">Email</Label>
          <Input
            id="login-email"
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
          <Label htmlFor="login-senha">Senha</Label>
          <Input
            id="login-senha"
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
  const { login } = useAuth()

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
    onIrPara('onboarding')
  }

  return (
    <div>
      <VoltarButton onClick={onVoltar} />

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
          <Label htmlFor="cadastro-username">Nome de usuário</Label>
          <Input
            id="cadastro-username"
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
          <Label htmlFor="cadastro-email">Email</Label>
          <Input
            id="cadastro-email"
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
          <Label htmlFor="cadastro-senha">Senha</Label>
          <Input
            id="cadastro-senha"
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
          <Label htmlFor="cadastro-confirmar-senha">Confirmar senha</Label>
          <Input
            id="cadastro-confirmar-senha"
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
                  id="cadastro-termos"
                  checked={field.value}
                  onCheckedChange={field.onChange}
                  className="mt-0.5"
                />
              )}
            />
            <Label htmlFor="cadastro-termos" className="font-normal">
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
    </div>
  )
}

const RASCUNHO_ONBOARDING_INICIAL: RascunhoOnboarding = {
  passo: 1,
  nivel: null,
  trilha: null,
  instituicao: '',
  curso: '',
  periodo: '',
  ementa: null,
}

export function BoasVindasPage() {
  const [modo, setModo] = useState<Modo>('escolha')
  const [rascunhoEntrar, setRascunhoEntrar] = useState<Partial<LoginFormValues>>({})
  const [rascunhoCadastro, setRascunhoCadastro] = useState<Partial<CadastroFormValues>>({})
  const [rascunhoEsqueci, setRascunhoEsqueci] = useState<Partial<EsqueciSenhaFormValues>>({})
  const [rascunhoOnboarding, setRascunhoOnboarding] = useState<RascunhoOnboarding>(
    RASCUNHO_ONBOARDING_INICIAL,
  )

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <div className="relative flex w-full flex-col items-center justify-center bg-primary px-8 py-12 text-primary-foreground md:w-1/2">
        <WelcomeCarousel />
      </div>

      <div className="flex w-full flex-col items-center justify-center px-8 py-12 md:w-1/2">
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
                <OnboardingWizard
                  onVoltarInicio={() => setModo('cadastro')}
                  rascunho={rascunhoOnboarding}
                  onRascunhoChange={setRascunhoOnboarding}
                />
              )}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
