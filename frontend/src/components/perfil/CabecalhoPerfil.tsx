import { motion } from 'framer-motion'
import { Flame, Star, Trophy } from 'lucide-react'
import { FotoPerfil } from '@/components/perfil/FotoPerfil'
import { useContagem } from '@/hooks/useContagem'
import { usePainel } from '@/hooks/useGamificacao'
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
  // O nível é do backend (`/gamificacao/me`), o mesmo da Home e do ranking. A
  // conta local (100 XP por nível) só vale até a resposta chegar: com ela, o
  // perfil dizia "nível 5" para quem a Home mostrava no nível 3.
  const painel = usePainel().data
  const { nivel, xpNoNivel, xpParaProximo, progresso } = painel
    ? {
        nivel: painel.nivel,
        xpNoNivel: painel.xp_no_nivel,
        xpParaProximo: painel.xp_para_o_proximo,
        progresso: painel.xp_no_nivel / Math.max(painel.xp_no_nivel + painel.xp_para_o_proximo, 1),
      }
    : calcularNivel(usuario.xp)

  return (
    <div className="relative flex flex-wrap items-center gap-4 overflow-hidden rounded-lg border border-border bg-card p-4 shadow-sm sm:gap-6 sm:p-6">
      <div
        aria-hidden
        className="pointer-events-none absolute -left-16 -top-24 size-64 rounded-full bg-accent/50 blur-3xl"
      />

      {/* No celular a foto vai em cima e o nome ganha a largura toda, em vez de virar "Lucas Andr…". */}
      <div className="relative flex min-w-0 flex-1 flex-col items-start gap-4 sm:flex-row sm:items-center sm:gap-5">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: 'spring', stiffness: 260, damping: 18 }}
          className="relative shrink-0"
        >
          <FotoPerfil usuario={usuario} />
          <span className="absolute -bottom-1 -right-1 rounded-full bg-primary px-2 py-0.5 font-display text-xs font-bold text-primary-foreground shadow">
            Nv. {nivel}
          </span>
        </motion.div>

        <div className="w-full min-w-0 flex-1">
          <h1 className="break-words font-display text-2xl font-bold leading-tight text-foreground sm:truncate sm:text-3xl">
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
