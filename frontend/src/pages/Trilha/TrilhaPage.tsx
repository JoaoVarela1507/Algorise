import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { motion, type Variants } from 'framer-motion'
import { ArrowLeft, ArrowRight, Award, Lock, PartyPopper, Star, Swords } from 'lucide-react'
import { CenarioOceano } from '@/components/trilha/CenarioOceano'
import { DetalheModulo } from '@/components/trilha/DetalheModulo'
import { MapaTrilha } from '@/components/trilha/MapaTrilha'
import { coresPeriodo } from '@/components/trilhas/periodos'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { modulosDaTrilha } from '@/mocks/modulos'
import { trilhasMock } from '@/mocks/trilhas'
import type { ModuloTrilha, TrilhaResumo } from '@/types/trilha'
import mascotePolvo from '@/assets/images/mascote-polvo.png'

const container: Variants = {
  oculto: {},
  visivel: { transition: { staggerChildren: 0.08 } },
}

const secao: Variants = {
  oculto: { opacity: 0, y: 16 },
  visivel: { opacity: 1, y: 0, transition: { duration: 0.4, ease: 'easeOut' } },
}

const doisDigitos = (n: number) => String(n).padStart(2, '0')

function Cabecalho({ trilha, numero }: { trilha: TrilhaResumo; numero: number }) {
  const navigate = useNavigate()
  const progresso = Math.round((trilha.modulosConcluidos / trilha.totalModulos) * 100)

  return (
    <div className="flex flex-wrap items-center gap-4 rounded-lg border border-border bg-card px-5 py-4 shadow-sm">
      <Button
        variant="ghost"
        size="icon"
        onClick={() => navigate('/trilhas')}
        aria-label="Voltar para as trilhas"
      >
        <ArrowLeft />
      </Button>

      <span className="flex size-12 shrink-0 items-center justify-center rounded-lg bg-secondary font-display text-xl font-extrabold text-foreground">
        {doisDigitos(numero)}
      </span>

      <div className="min-w-0 flex-1">
        <h1 className="truncate font-display text-2xl font-bold text-foreground">{trilha.nome}</h1>
        <div className="flex flex-wrap items-center gap-2 text-xs font-bold">
          <span className="rounded-full bg-secondary px-2.5 py-0.5 text-muted-foreground">
            {trilha.categoria}
          </span>
          <span
            className={cn(
              'rounded-full px-2.5 py-0.5 text-periodo-foreground',
              coresPeriodo[trilha.periodo]?.cheio,
            )}
          >
            {trilha.periodo}º Período
          </span>
          <span className="text-muted-foreground">{trilha.motivo}</span>
        </div>
      </div>

      <div className="flex w-full items-center gap-3 sm:w-72">
        <div
          className="h-3 flex-1 overflow-hidden rounded-full bg-muted"
          role="progressbar"
          aria-label="Módulos concluídos"
          aria-valuemin={0}
          aria-valuemax={trilha.totalModulos}
          aria-valuenow={trilha.modulosConcluidos}
        >
          <motion.div
            className="h-full rounded-full bg-success"
            initial={{ width: 0 }}
            animate={{ width: `${progresso}%` }}
            transition={{ delay: 0.3, duration: 0.8, ease: 'easeOut' }}
          />
        </div>
        <span className="rounded-full border border-border px-3 py-1 font-display font-bold text-streak">
          {trilha.modulosConcluidos}/{trilha.totalModulos}
        </span>
      </div>
    </div>
  )
}

function Parabens({ trilha }: { trilha: TrilhaResumo }) {
  return (
    <div className="relative flex h-full flex-col gap-4 overflow-hidden">
      {/* Confete: pontinhos caindo, como os "✦" do protótipo. */}
      {Array.from({ length: 10 }, (_, i) => (
        <motion.span
          key={i}
          aria-hidden
          className={cn(
            'pointer-events-none absolute size-2 rounded-sm',
            ['bg-primary', 'bg-xp', 'bg-success', 'bg-periodo-2', 'bg-periodo-7'][i % 5],
          )}
          style={{ left: `${8 + i * 9}%` }}
          initial={{ top: '-5%', opacity: 0, rotate: 0 }}
          animate={{ top: '105%', opacity: [0, 1, 1, 0], rotate: 360 }}
          transition={{ duration: 3 + (i % 3), repeat: Infinity, delay: i * 0.35, ease: 'linear' }}
        />
      ))}

      <div className="relative flex items-center gap-3">
        <motion.span
          animate={{ rotate: [0, -15, 15, 0] }}
          transition={{ duration: 1.5, repeat: Infinity }}
          className="flex size-11 items-center justify-center rounded-full bg-xp/25 text-streak"
        >
          <PartyPopper className="size-6" aria-hidden />
        </motion.span>
        <p className="text-foreground">
          <strong>Parabéns!</strong> Excelente caminhada até aqui: você demonstrou bom{' '}
          <strong>domínio</strong> no assunto!
        </p>
      </div>

      <Button asChild size="lg" full className="group relative">
        <Link to={`/trilhas/${trilha.id}/questao/desafio`}>
          <Swords />
          Fazer desafio proposto
        </Link>
      </Button>

      <p className="relative text-center text-sm font-bold text-muted-foreground">
        ou, para se especializar mais, acesse os certificados parceiros:
      </p>

      <Link
        to="/certificados"
        className="group relative flex items-center gap-3 rounded-lg border border-border bg-background p-3 transition-colors hover:border-primary/50"
      >
        <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary">
          <Award className="size-5" aria-hidden />
        </span>
        <span className="flex-1 font-semibold text-foreground">{trilha.nome}</span>
        <ArrowRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-1" />
      </Link>
    </div>
  )
}

function ResumoTrilha({ trilha, modulos }: { trilha: TrilhaResumo; modulos: ModuloTrilha[] }) {
  const xpTotal = modulos.reduce((soma, m) => soma + m.xp, 0)
  const xpGanho = modulos.filter((m) => m.status === 'concluido').reduce((s, m) => s + m.xp, 0)
  const restantes = modulos.length - trilha.modulosConcluidos

  return (
    <div className="flex h-full items-center gap-5">
      <motion.img
        src={mascotePolvo}
        alt=""
        className="hidden h-24 shrink-0 select-none sm:block"
        draggable={false}
        animate={{ rotate: [0, -4, 4, 0] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
      />
      <div className="flex-1">
        <p className="font-display text-lg font-bold text-foreground">
          {trilha.modulosConcluidos === 0
            ? 'Bora começar essa trilha?'
            : `Faltam ${restantes} ${restantes === 1 ? 'módulo' : 'módulos'}, continue assim!`}
        </p>
        <p className="text-sm text-muted-foreground">
          Conclua todos os módulos para liberar o desafio final e o certificado do parceiro.
        </p>
        <div className="mt-3 flex flex-wrap gap-3 text-sm font-semibold">
          <span className="flex items-center gap-1.5 rounded-lg bg-secondary/60 px-3 py-1.5">
            <Star className="size-4 fill-xp text-xp" aria-hidden />
            {xpGanho} / {xpTotal} XP
          </span>
          <span className="flex items-center gap-1.5 rounded-lg bg-secondary/60 px-3 py-1.5">
            <Award className="size-4 text-primary" aria-hidden />
            Certificado ao concluir
          </span>
        </div>
      </div>
    </div>
  )
}

export function TrilhaPage() {
  const { trilhaId } = useParams()
  const indice = trilhasMock.findIndex((t) => t.id === trilhaId)
  const trilha = indice >= 0 ? trilhasMock[indice] : undefined
  const modulos = trilha ? modulosDaTrilha(trilha) : []
  const atual = modulos.find((m) => m.status === 'atual')
  const [selecionado, setSelecionado] = useState(atual?.ordem ?? modulos.length ?? 1)

  if (!trilha) {
    return (
      <div className="flex min-h-full flex-col items-center justify-center gap-3 text-center">
        <img src={mascotePolvo} alt="" className="h-28" />
        <h1 className="font-display text-2xl font-bold text-foreground">Trilha não encontrada</h1>
        <Button asChild variant="outline">
          <Link to="/trilhas">Ver todas as trilhas</Link>
        </Button>
      </div>
    )
  }

  const terminou = trilha.modulosConcluidos >= trilha.totalModulos
  const moduloSelecionado = modulos.find((m) => m.ordem === selecionado) ?? modulos[0]

  return (
    <motion.div
      variants={container}
      initial="oculto"
      animate="visivel"
      className="flex h-full flex-col gap-6"
    >
      <motion.section variants={secao}>
        <Cabecalho trilha={trilha} numero={indice + 1} />
      </motion.section>

      {trilha.bloqueada && (
        <motion.p
          variants={secao}
          className="flex items-center gap-2 rounded-lg border border-dashed border-border bg-card p-4 text-muted-foreground"
        >
          <Lock className="size-5 shrink-0 text-locked" aria-hidden />
          Esta trilha ainda está bloqueada. Conclua <strong>{trilha.requisito}</strong> para liberar
          os módulos.
        </motion.p>
      )}

      {/*
        Mapa à esquerda, com scroll só por dentro (a trilha pode ter muitos
        módulos); detalhe e resumo fixos à direita. A página não rola.
      */}
      <div className="grid min-h-0 flex-1 gap-6 lg:grid-cols-[minmax(0,1fr)_26rem]">
        <motion.section
          variants={secao}
          className="relative h-[32rem] overflow-hidden rounded-lg border border-border bg-card shadow-sm lg:h-auto lg:min-h-0"
          aria-label="Mapa de módulos"
        >
          <CenarioOceano />
          <MapaTrilha modulos={modulos} selecionado={selecionado} onSelecionar={setSelecionado} />
        </motion.section>

        <div className="flex min-h-0 flex-col gap-6">
          <motion.section
            variants={secao}
            className="flex min-h-0 flex-1 flex-col rounded-lg border border-border bg-card p-6 shadow-sm"
          >
            {moduloSelecionado && <DetalheModulo trilhaId={trilha.id} modulo={moduloSelecionado} />}
          </motion.section>
          <motion.section
            variants={secao}
            className={cn(
              'rounded-lg border p-6 shadow-sm',
              terminou ? 'border-xp/50 bg-xp/10' : 'border-border bg-card',
            )}
          >
            {terminou ? (
              <Parabens trilha={trilha} />
            ) : (
              <ResumoTrilha trilha={trilha} modulos={modulos} />
            )}
          </motion.section>
        </div>
      </div>
    </motion.div>
  )
}
