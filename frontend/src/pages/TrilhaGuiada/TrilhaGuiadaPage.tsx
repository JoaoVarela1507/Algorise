import { Link } from 'react-router-dom'
import { CheckCircle2, Clock, Lock, PlayCircle } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Carregando, ErroAoCarregar, Vazio } from '@/components/ui/estados'
import { Progress } from '@/components/ui/progress'
import { useTrilhaGuiada } from '@/hooks/useEmenta'
import { ApiError } from '@/services/api'
import type { ItemGuiado } from '@/services/ementa'

/** Os itens seguidos da mesma disciplina, para a tela agrupar sob um título. */
function porDisciplina(itens: ItemGuiado[]): { disciplina: string; itens: ItemGuiado[] }[] {
  const grupos: { disciplina: string; itens: ItemGuiado[] }[] = []
  for (const item of itens) {
    const ultimo = grupos[grupos.length - 1]
    if (ultimo?.disciplina === item.disciplina) ultimo.itens.push(item)
    else grupos.push({ disciplina: item.disciplina, itens: [item] })
  }
  return grupos
}

function Modulo({ item }: { item: ItemGuiado }) {
  const modulo = item.modulo
  if (!modulo) return null
  const bloqueado = modulo.status === 'bloqueado'
  const Icone = modulo.status === 'concluido' ? CheckCircle2 : bloqueado ? Lock : PlayCircle
  const rotulo = { concluido: 'Concluído', bloqueado: 'Bloqueado', 'em-andamento': 'Liberado' }[
    modulo.status
  ]

  const corpo = (
    <>
      <Icone
        className={bloqueado ? 'size-6 shrink-0 text-locked' : 'size-6 shrink-0 text-primary'}
        aria-label={rotulo}
      />
      <div className="min-w-0 flex-1">
        <p className="font-bold text-foreground">{modulo.titulo}</p>
        <p className="text-sm text-muted-foreground">
          {modulo.trilha_nome} · passo {modulo.ordem}
        </p>
        {item.assuntos.length > 0 && (
          <p className="mt-1 text-sm text-muted-foreground">{item.assuntos.join(' · ')}</p>
        )}
      </div>
      {item.base && <Badge variant="outline">Base</Badge>}
    </>
  )

  const classes = 'flex items-center gap-3 rounded-lg border border-border bg-card p-4 shadow-sm'
  return bloqueado ? (
    <div className={`${classes} opacity-70`}>{corpo}</div>
  ) : (
    <Link
      to={`/trilhas/${modulo.trilha_slug}/questao/${modulo.ordem}`}
      className={`${classes} transition-colors hover:border-primary`}
    >
      {corpo}
    </Link>
  )
}

function Lacuna({ item }: { item: ItemGuiado }) {
  const semConteudo = item.status_lacuna === 'sem_conteudo'
  return (
    <div className="flex items-center gap-3 rounded-lg border border-dashed border-border p-4">
      <Clock className="size-6 shrink-0 text-muted-foreground" aria-hidden />
      <p className="min-w-0 flex-1 text-foreground">{item.assuntos.join(' · ')}</p>
      <Badge variant="secondary">{semConteudo ? 'Sem conteúdo ainda' : 'Em preparação'}</Badge>
    </div>
  )
}

/**
 * A trilha guiada do aluno (#38): os assuntos da ementa, em ordem de estudo.
 *
 * Cada módulo leva ao passo da trilha do catálogo que o cobre; o que o
 * catálogo ainda não tem aparece "em preparação", até a busca de conteúdo
 * (#207) preencher.
 */
export function TrilhaGuiadaPage() {
  const trilha = useTrilhaGuiada()

  if (trilha.isPending) return <Carregando rotulo="Montando sua trilha guiada…" />
  if (trilha.isError) {
    if (trilha.error instanceof ApiError && trilha.error.status === 404) {
      return (
        <Vazio
          titulo="Sua trilha guiada ainda não foi gerada"
          descricao="Revise os assuntos que encontramos na sua ementa e confirme para gerar a trilha."
          acao={
            <Button asChild>
              <Link to="/trilha-guiada/revisao">Revisar a ementa</Link>
            </Button>
          }
        />
      )
    }
    return <ErroAoCarregar erro={trilha.error} aoTentarDeNovo={() => void trilha.refetch()} />
  }

  const { itens, total_modulos: total, concluidos } = trilha.data
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-foreground">Sua trilha guiada</h1>
          <p className="text-muted-foreground">
            {concluidos} de {total} {total === 1 ? 'módulo concluído' : 'módulos concluídos'}
          </p>
        </div>
        <Button asChild variant="secondary">
          <Link to="/trilha-guiada/revisao">Revisar assuntos</Link>
        </Button>
      </header>
      <Progress value={total ? (concluidos / total) * 100 : 0} aria-label="Progresso da trilha" />

      {porDisciplina(itens).map((grupo, i) => (
        <section key={`${grupo.disciplina}-${i}`} className="flex flex-col gap-3">
          <h2 className="font-display text-lg font-bold text-foreground">{grupo.disciplina}</h2>
          <ol className="flex flex-col gap-3">
            {grupo.itens.map((item, j) => (
              <li key={item.modulo ? `m${item.modulo.id}` : `l${j}`}>
                {item.tipo === 'modulo' ? <Modulo item={item} /> : <Lacuna item={item} />}
              </li>
            ))}
          </ol>
        </section>
      ))}
    </div>
  )
}
