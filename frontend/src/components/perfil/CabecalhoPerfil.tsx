import { motion } from 'framer-motion'
import { Flame, Star, Trophy } from 'lucide-react'
import { AvatarIniciais } from '@/components/home/AvatarIniciais'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { useContagem } from '@/hooks/useContagem'
import { calcularNivel } from '@/lib/nivel'
import type { Usuario } from '@/types/usuario'

const formatar = new Intl.NumberFormat('pt-BR')

function Estatistica({
  icone: Icone,
  valor,
  rotulo,
  cor,
}: {
  icone: typeof Star
  valor: number
  rotulo: string
  cor: string
}) {
  const contagem = useContagem(valor, { atraso: 0.3 })
  return (
    <div className="flex items-center gap-3 rounded-lg bg-secondary/60 px-4 py-3">
      <Icone className={`size-6 ${cor}`} aria-hidden />
      <div>
        <p className="font-display text-2xl font-extrabold leading-none text-foreground">
          <span aria-hidden>{formatar.format(contagem)}</span>
          <span className="sr-only">{formatar.format(valor)}</span>
        </p>
        <p className="text-xs font-semibold text-muted-foreground">{rotulo}</p>
      </div>
    </div>
  )
}

export function CabecalhoPerfil({ usuario }: { usuario: Usuario }) {
  const { nivel, xpNoNivel, xpParaProximo, progresso } = calcularNivel(usuario.xp)

  return (
    <div className="relative flex flex-wrap items-center gap-6 overflow-hidden rounded-lg border border-border bg-card p-6 shadow-sm">
      <div
        aria-hidden
        className="pointer-events-none absolute -left-16 -top-24 size-64 rounded-full bg-accent/50 blur-3xl"
      />

      <div className="relative flex min-w-0 flex-1 items-center gap-5">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: 'spring', stiffness: 260, damping: 18 }}
          className="relative shrink-0"
        >
          {usuario.avatarUrl ? (
            <Avatar className="size-24 ring-4 ring-primary/30">
              <AvatarImage src={usuario.avatarUrl} alt="" />
              <AvatarFallback>{usuario.nome[0]}</AvatarFallback>
            </Avatar>
          ) : (
            <AvatarIniciais
              nome={usuario.nome}
              className="size-24 text-3xl ring-4 ring-primary/30"
            />
          )}
          <span className="absolute -bottom-1 -right-1 rounded-full bg-primary px-2 py-0.5 font-display text-xs font-bold text-primary-foreground shadow">
            Nv. {nivel}
          </span>
        </motion.div>

        <div className="min-w-0 flex-1">
          <h1 className="truncate font-display text-3xl font-bold text-foreground">
            {usuario.nome}
          </h1>
          <p className="truncate text-sm text-muted-foreground">
            {usuario.username && `@${usuario.username} · `}
            {usuario.email}
          </p>

          <div className="mt-3 max-w-md">
            <div className="mb-1 flex justify-between text-xs font-bold">
              <span className="text-foreground">
                Nível {nivel} · {formatar.format(xpNoNivel)} XP
              </span>
              <span className="text-muted-foreground">
                faltam {formatar.format(xpParaProximo)} XP para o nível {nivel + 1}
              </span>
            </div>
            <div
              className="h-2.5 overflow-hidden rounded-full bg-muted"
              role="progressbar"
              aria-label="Progresso até o próximo nível"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round(progresso * 100)}
            >
              <motion.div
                className="h-full rounded-full bg-gradient-to-r from-xp to-streak"
                initial={{ width: 0 }}
                animate={{ width: `${progresso * 100}%` }}
                transition={{ delay: 0.3, duration: 0.8, ease: 'easeOut' }}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="relative grid w-full grid-cols-3 gap-3 sm:w-auto">
        <Estatistica icone={Star} valor={usuario.xp} rotulo="XP total" cor="fill-xp text-xp" />
        <Estatistica
          icone={Flame}
          valor={usuario.streakDias}
          rotulo={usuario.streakDias === 1 ? 'dia seguido' : 'dias seguidos'}
          cor="fill-streak/30 text-streak"
        />
        <Estatistica icone={Trophy} valor={nivel} rotulo="nível" cor="text-primary" />
      </div>
    </div>
  )
}
