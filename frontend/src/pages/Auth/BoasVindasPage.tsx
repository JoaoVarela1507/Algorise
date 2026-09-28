import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useAuth } from '@/contexts/AuthContext'
import logoAlgorise from '@/assets/images/logo-algorise.png'
import carrosselDuvidasAcademicas from '@/assets/images/carrossel-duvidas-academicas.png'
import carrosselPolvoBanheira from '@/assets/images/carrossel-polvo-banheira.png'
import carrosselEmentasFaculdade from '@/assets/images/carrossel-ementas-faculdade.png'

// Login de teste enquanto não há backend de autenticação real.
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

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="size-5" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M23.52 12.27c0-.85-.08-1.67-.22-2.45H12v4.63h6.46c-.28 1.5-1.13 2.77-2.4 3.62v3h3.88c2.27-2.09 3.58-5.17 3.58-8.8Z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.24 0 5.96-1.07 7.94-2.92l-3.88-3c-1.08.72-2.45 1.15-4.06 1.15-3.12 0-5.77-2.11-6.71-4.94H1.28v3.1C3.25 21.3 7.31 24 12 24Z"
      />
      <path
        fill="#FBBC05"
        d="M5.29 14.29a7.25 7.25 0 0 1 0-4.58v-3.1H1.28a12 12 0 0 0 0 10.78l4.01-3.1Z"
      />
      <path
        fill="#EA4335"
        d="M12 4.75c1.76 0 3.34.61 4.59 1.8l3.44-3.44C17.95 1.19 15.24 0 12 0 7.31 0 3.25 2.7 1.28 6.61l4.01 3.1C6.23 6.87 8.88 4.75 12 4.75Z"
      />
    </svg>
  )
}

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

export function BoasVindasPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState(false)

  function handleSubmit(event: FormEvent) {
    event.preventDefault()

    if (email !== LOGIN_TESTE.email || senha !== LOGIN_TESTE.senha) {
      setErro(true)
      return
    }

    setErro(false)
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
    <div className="flex min-h-screen flex-col md:flex-row">
      <div className="relative flex w-full flex-col items-center justify-center bg-primary px-8 py-12 text-primary-foreground md:w-1/2">
        <WelcomeCarousel />
      </div>

      <div className="flex w-full flex-col items-center justify-center px-8 py-12 md:w-1/2">
        <div className="w-full max-w-sm">
          <img src={logoAlgorise} alt="Algorise" className="mx-auto mb-6 h-48" />

          <p className="text-center text-lg text-foreground">
            <span className="font-bold">Descubra</span> um jeito mais{' '}
            <span className="font-bold">inteligente</span> de aprender{' '}
            <span className="font-bold">programação</span> com conteúdos adaptados ao{' '}
            <span className="font-bold">seu</span> curso.
          </p>

          <form className="mt-8 flex flex-col gap-4" onSubmit={handleSubmit}>
            <div className="flex flex-col gap-1">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="voce@exemplo.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </div>
            <div className="flex flex-col gap-1">
              <Label htmlFor="senha">Senha</Label>
              <Input
                id="senha"
                type="password"
                placeholder="Digite sua senha"
                value={senha}
                onChange={(event) => setSenha(event.target.value)}
                required
                minLength={8}
              />
            </div>

            {erro && (
              <p role="alert" className="text-sm font-semibold text-destructive">
                Email ou senha incorretos.
              </p>
            )}

            <div className="my-2 flex items-center gap-3 text-sm text-muted-foreground">
              <span className="h-px flex-1 bg-border" />
              ou use a conta Google
              <span className="h-px flex-1 bg-border" />
            </div>

            <Button type="button" variant="secondary" full size="lg">
              <GoogleIcon />
              Continuar com Google
            </Button>

            <Button type="submit" full size="lg" className="mt-2">
              Entrar
            </Button>
          </form>

          <p className="mt-4 rounded-lg border border-dashed border-border bg-muted/50 p-3 text-center text-xs text-muted-foreground">
            Login de teste (dev): <span className="font-mono">{LOGIN_TESTE.email}</span> /{' '}
            <span className="font-mono">{LOGIN_TESTE.senha}</span>
          </p>

          <p className="mt-4 text-center text-sm text-muted-foreground">
            Não tem uma conta?{' '}
            <Link to="/cadastro" className="font-semibold text-primary hover:underline">
              Criar conta
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
