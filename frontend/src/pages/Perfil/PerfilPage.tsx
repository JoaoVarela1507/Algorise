import { Link } from 'react-router-dom'
import { motion, type Variants } from 'framer-motion'
import { ArrowRight, Award, BadgeCheck, Share2, Sparkles, Trophy } from 'lucide-react'
import { CabecalhoPerfil } from '@/components/perfil/CabecalhoPerfil'
import { CaminhoCard } from '@/components/perfil/CaminhoCard'
import { DadosAcademicosCard } from '@/components/perfil/DadosAcademicosCard'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/contexts/AuthContext'

const container: Variants = {
  oculto: {},
  visivel: { transition: { staggerChildren: 0.08 } },
}

const secao: Variants = {
  oculto: { opacity: 0, y: 16 },
  visivel: { opacity: 1, y: 0, transition: { duration: 0.4, ease: 'easeOut' } },
}

const passos = [
  { icone: Trophy, texto: 'Conclua todos os módulos de uma trilha' },
  { icone: BadgeCheck, texto: 'Receba o certificado com código de validação' },
  { icone: Share2, texto: 'Compartilhe no LinkedIn e no currículo' },
]

// Brilhos em volta da medalha: posição e atraso de cada um.
const brilhos = [
  { classe: 'left-[18%] top-[12%] size-5', atraso: 0 },
  { classe: 'right-[16%] top-[22%] size-4', atraso: 0.6 },
  { classe: 'left-[24%] bottom-[14%] size-3', atraso: 1.2 },
  { classe: 'right-[22%] bottom-[10%] size-5', atraso: 1.8 },
]

function CertificadosCard() {
  return (
    <div className="relative flex h-full flex-col gap-6 overflow-hidden rounded-lg bg-gradient-to-br from-primary to-streak p-6 text-primary-foreground shadow-md">
      <div
        aria-hidden
        className="pointer-events-none absolute -right-20 -top-20 size-64 rounded-full bg-primary-foreground/10 blur-2xl"
      />

      <div className="relative">
        <h2 className="font-display text-2xl font-bold">Seus certificados</h2>
        <p className="text-primary-foreground/90">
          Veja e compartilhe os certificados das trilhas que você concluiu.
        </p>
      </div>

      {/* Medalha no centro, ocupando o espaço livre do card. */}
      <div className="relative flex flex-1 items-center justify-center py-4" aria-hidden>
        <motion.span
          className="absolute size-40 rounded-full bg-xp/40 blur-2xl"
          animate={{ scale: [0.9, 1.1, 0.9], opacity: [0.6, 1, 0.6] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.span
          className="relative flex size-36 items-center justify-center rounded-full bg-primary-foreground/20 ring-8 ring-primary-foreground/10"
          animate={{ y: [0, -8, 0], rotate: [0, -4, 4, 0] }}
          transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
        >
          <Award className="size-20 drop-shadow-md" strokeWidth={1.75} />
        </motion.span>
        {brilhos.map((brilho) => (
          <motion.span
            key={brilho.classe}
            className={`absolute ${brilho.classe}`}
            animate={{ scale: [0, 1, 0], rotate: [0, 90, 180] }}
            transition={{ duration: 2.4, repeat: Infinity, delay: brilho.atraso }}
          >
            <Sparkles className="size-full text-xp" />
          </motion.span>
        ))}
      </div>

      <ol className="relative flex flex-col gap-2">
        {passos.map((passo, i) => (
          <motion.li
            key={passo.texto}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4 + i * 0.1 }}
            className="flex items-center gap-3 rounded-lg bg-primary-foreground/15 px-4 py-3"
          >
            <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary-foreground font-display font-bold text-primary">
              {i + 1}
            </span>
            <passo.icone className="size-5 shrink-0" aria-hidden />
            <span className="text-sm font-semibold">{passo.texto}</span>
          </motion.li>
        ))}
      </ol>

      <Button
        asChild
        variant="secondary"
        size="lg"
        full
        className="group relative bg-card text-primary hover:bg-card/90"
      >
        <Link to="/certificados">
          Seguir para certificados
          <ArrowRight className="transition-transform group-hover:translate-x-1" />
        </Link>
      </Button>
    </div>
  )
}

export function PerfilPage() {
  const { usuario } = useAuth()
  // A rota fica atrás do RequireAuth, então o usuário sempre existe aqui.
  if (!usuario) return null

  return (
    <motion.div
      variants={container}
      initial="oculto"
      animate="visivel"
      className="flex min-h-full flex-col gap-6"
    >
      <motion.section variants={secao}>
        <CabecalhoPerfil usuario={usuario} />
      </motion.section>

      <div className="grid flex-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
        <motion.section variants={secao}>
          <DadosAcademicosCard usuario={usuario} />
        </motion.section>
        <motion.section variants={secao}>
          <CaminhoCard usuario={usuario} />
        </motion.section>
        <motion.section variants={secao} className="md:col-span-2 xl:col-span-1">
          <CertificadosCard />
        </motion.section>
      </div>
    </motion.div>
  )
}
