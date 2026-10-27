import { Link } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import {
  ArrowDownUp,
  ArrowRight,
  Check,
  CheckCircle2,
  Clock,
  Code2,
  ListChecks,
  Lock,
  MessageSquareText,
  Play,
  RotateCcw,
  Sparkles,
  Star,
  Terminal,
  TextCursorInput,
  type LucideIcon,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { atividadesDoModulo } from '@/mocks/modulos'
import type { AtividadeModulo, ModuloTrilha, TipoAtividade } from '@/types/trilha'

const estados = {
  concluido: { rotulo: 'Concluído', classe: 'bg-success/15 text-success', icone: CheckCircle2 },
  atual: { rotulo: 'Próximo módulo', classe: 'bg-primary/15 text-primary', icone: Sparkles },
  bloqueado: { rotulo: 'Bloqueado', classe: 'bg-muted text-locked', icone: Lock },
} as const

// Cor e ícone de cada formato de atividade (telas 28 a 34).
const tipos: Record<TipoAtividade, { rotulo: string; icone: LucideIcon; cor: string }> = {
  'multipla-escolha': {
    rotulo: 'Múltipla escolha',
    icone: ListChecks,
    cor: 'bg-periodo-2/30 text-periodo-foreground',
  },
  'preencher-lacuna': {
    rotulo: 'Preencher lacunas',
    icone: TextCursorInput,
    cor: 'bg-periodo-3/35 text-periodo-foreground',
  },
  ordenacao: {
    rotulo: 'Ordenação',
    icone: ArrowDownUp,
    cor: 'bg-periodo-6/35 text-periodo-foreground',
  },
  terminal: { rotulo: 'Terminal', icone: Terminal, cor: 'bg-periodo-5/35 text-periodo-foreground' },
  'resposta-aberta': {
    rotulo: 'Resposta aberta',
    icone: MessageSquareText,
    cor: 'bg-periodo-7/35 text-periodo-foreground',
  },
  'desafio-codigo': {
    rotulo: 'Desafio de código',
    icone: Code2,
    cor: 'bg-primary/25 text-periodo-foreground',
  },
}

function ItemAtividade({
  atividade,
  indice,
  destino,
}: {
  atividade: AtividadeModulo
  indice: number
  destino: string
}) {
  const tipo = tipos[atividade.tipo]
  const bloqueada = atividade.status === 'bloqueada'
  const proxima = atividade.status === 'proxima'

  const conteudo = (
    <>
      <span
        className={cn(
          'flex size-10 shrink-0 items-center justify-center rounded-lg',
          bloqueada ? 'bg-muted text-locked' : tipo.cor,
        )}
      >
        <tipo.icone className="size-5" aria-hidden />
      </span>
      <span className="min-w-0 flex-1">
        <span
          className={cn(
            'block truncate text-sm font-semibold',
            bloqueada ? 'text-muted-foreground' : 'text-foreground',
          )}
        >
          {atividade.titulo}
        </span>
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
          {tipo.rotulo}
          <span aria-hidden>·</span>
          <Clock className="size-3" aria-hidden />
          {atividade.minutos} min
        </span>
      </span>
      <span
        className={cn(
          'flex size-7 shrink-0 items-center justify-center rounded-full',
          atividade.status === 'feita' && 'bg-success text-success-foreground',
          proxima && 'bg-primary text-primary-foreground',
          atividade.status === 'pendente' && 'border-2 border-border',
          bloqueada && 'text-locked',
        )}
        aria-label={
          {
            feita: 'Feita',
            proxima: 'Próxima',
            pendente: 'Pendente',
            bloqueada: 'Bloqueada',
          }[atividade.status]
        }
      >
        {atividade.status === 'feita' && <Check className="size-4" strokeWidth={3} />}
        {proxima && <Play className="ml-0.5 size-3.5 fill-current" />}
        {bloqueada && <Lock className="size-4" />}
      </span>
    </>
  )

  const classe = cn(
    'flex items-center gap-3 rounded-lg border p-2.5 transition-colors',
    proxima ? 'border-primary/40 bg-primary/5' : 'border-border',
  )

  return (
    <motion.li
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.05 * indice }}
    >
      {bloqueada ? (
        <div className={classe}>{conteudo}</div>
      ) : (
        <Link to={destino} className={cn(classe, 'hover:border-primary/50 hover:bg-muted/40')}>
          {conteudo}
        </Link>
      )}
    </motion.li>
  )
}

export function DetalheModulo({ trilhaId, modulo }: { trilhaId: string; modulo: ModuloTrilha }) {
  const estado = estados[modulo.status]
  const atividades = atividadesDoModulo(modulo)
  const feitas = atividades.filter((a) => a.status === 'feita').length
  const minutos = atividades.reduce((soma, a) => soma + a.minutos, 0)
  const destino = `/trilhas/${trilhaId}/questao/${modulo.ordem}`

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={modulo.id}
        initial={{ opacity: 0, x: 12 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -12 }}
        transition={{ duration: 0.2 }}
        className="flex h-full min-h-0 flex-col"
      >
        <span
          className={cn(
            'flex items-center gap-1.5 self-start rounded-full px-3 py-1 text-xs font-bold',
            estado.classe,
          )}
        >
          <estado.icone className="size-3.5" aria-hidden />
          {estado.rotulo}
        </span>
        <h2 className="mt-3 font-display text-2xl font-bold text-foreground">
          <span className="text-muted-foreground">{modulo.ordem}.</span> {modulo.titulo}
        </h2>
        <p className="text-muted-foreground">{modulo.descricao}</p>

        <div className="mt-4 flex flex-wrap gap-2">
          <span className="flex items-center gap-1.5 rounded-lg bg-secondary/60 px-3 py-1.5 text-sm font-semibold text-foreground">
            <ListChecks className="size-4 text-primary" aria-hidden />
            {feitas}/{atividades.length} atividades
          </span>
          <span className="flex items-center gap-1.5 rounded-lg bg-secondary/60 px-3 py-1.5 text-sm font-semibold text-foreground">
            <Clock className="size-4 text-primary" aria-hidden />~{minutos} min
          </span>
          <span className="flex items-center gap-1.5 rounded-lg bg-secondary/60 px-3 py-1.5 text-sm font-semibold text-foreground">
            <Star className="size-4 fill-xp text-xp" aria-hidden />+{modulo.xp} XP
          </span>
        </div>

        <p className="mb-2 mt-5 text-xs font-bold uppercase tracking-wide text-muted-foreground">
          Atividades
        </p>
        {/* Rola por dentro se o módulo tiver muitas atividades. */}
        <ol className="-mr-2 flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pr-2">
          {atividades.map((atividade, i) => (
            <ItemAtividade key={atividade.id} atividade={atividade} indice={i} destino={destino} />
          ))}
        </ol>

        <div className="pt-4">
          {modulo.status === 'bloqueado' ? (
            <p className="flex items-center gap-2 rounded-lg border border-dashed border-border p-3 text-sm text-muted-foreground">
              <Lock className="size-4 shrink-0" aria-hidden />
              Conclua o módulo {modulo.ordem - 1} para desbloquear este.
            </p>
          ) : (
            <Button
              asChild
              size="lg"
              full
              variant={modulo.status === 'concluido' ? 'secondary' : 'default'}
              className="group"
            >
              <Link to={destino}>
                {modulo.status === 'concluido' ? (
                  <>
                    <RotateCcw />
                    Revisar módulo
                  </>
                ) : (
                  <>
                    {modulo.ordem === 1 ? 'Começar módulo' : 'Continuar módulo'}
                    <ArrowRight className="transition-transform group-hover:translate-x-1" />
                  </>
                )}
              </Link>
            </Button>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  )
}
