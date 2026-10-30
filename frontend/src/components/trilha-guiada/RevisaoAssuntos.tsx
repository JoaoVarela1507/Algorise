import { useRef, useState, type FormEvent } from 'react'
import { Plus, X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { mensagemDeErro } from '@/lib/erros'
import type { DisciplinaLida, DisciplinaRevisada } from '@/services/ementa'

type AssuntoLido = DisciplinaLida['assuntos'][number]

interface AssuntoEditavel {
  chave: number
  texto: string
  // O que o servidor leu, para a badge dizer se está no catálogo. Sem ele, o
  // assunto é novo ou foi renomeado, e só tem situação depois de salvar.
  lido?: AssuntoLido
}

interface DisciplinaEditavel {
  chave: number
  nome: string
  periodo?: number | null
  carga_horaria?: number | null
  // Entra na trilha guiada. A IA marca as de programação; o aluno corrige.
  na_trilha: boolean
  assuntos: AssuntoEditavel[]
}

/** O corpo do `PUT`: sem assunto em branco e sem disciplina vazia. */
function paraRevisao(disciplinas: DisciplinaEditavel[]): DisciplinaRevisada[] {
  return disciplinas
    .map((disciplina) => ({
      nome: disciplina.nome,
      periodo: disciplina.periodo ?? null,
      carga_horaria: disciplina.carga_horaria ?? null,
      na_trilha: disciplina.na_trilha,
      assuntos: disciplina.assuntos.map((a) => a.texto.trim()).filter(Boolean),
    }))
    .filter((disciplina) => disciplina.assuntos.length > 0)
}

function Situacao({ assunto }: { assunto: AssuntoEditavel }) {
  const lido = assunto.lido
  // Fora da trilha no servidor e marcada agora: vai ao catálogo ao salvar.
  if (!lido || lido.texto !== assunto.texto.trim() || lido.situacao === 'fora') {
    return <Badge variant="outline">Novo</Badge>
  }
  if (lido.situacao === 'coberto') {
    return <Badge variant="success">No catálogo</Badge>
  }
  return <Badge variant="secondary">Em preparação</Badge>
}

/**
 * A lista de disciplinas e assuntos lidos da ementa, editável (#38).
 *
 * O aluno corrige o texto, remove o que não é dele e acrescenta o que a IA não
 * viu. Nada vai ao servidor até salvar ou confirmar; e o servidor só busca de
 * novo no catálogo o que mudou.
 */
export function RevisaoAssuntos({
  disciplinas: lidas,
  salvando,
  erro,
  aoSalvar,
  aoConfirmar,
}: {
  disciplinas: DisciplinaLida[]
  salvando: boolean
  erro: unknown
  aoSalvar: (disciplinas: DisciplinaRevisada[]) => void
  aoConfirmar: (disciplinas: DisciplinaRevisada[], alterada: boolean) => void
}) {
  const proximaChave = useRef(0)
  const nova = () => proximaChave.current++

  const [disciplinas, setDisciplinas] = useState<DisciplinaEditavel[]>(() =>
    lidas.map((disciplina) => ({
      chave: nova(),
      nome: disciplina.nome,
      periodo: disciplina.periodo,
      carga_horaria: disciplina.carga_horaria,
      na_trilha: disciplina.na_trilha,
      assuntos: disciplina.assuntos.map((lido) => ({ chave: nova(), texto: lido.texto, lido })),
    })),
  )
  const [rascunhos, setRascunhos] = useState<Record<number, string>>({})

  const revisao = paraRevisao(disciplinas)
  const original = JSON.stringify(
    paraRevisao(
      lidas.map((d) => ({
        ...d,
        chave: 0,
        assuntos: d.assuntos.map((a) => ({ chave: 0, texto: a.texto })),
      })),
    ),
  )
  const alterada = JSON.stringify(revisao) !== original
  const vazia = !revisao.some((disciplina) => disciplina.na_trilha)

  function alternarTrilha(disciplina: number, naTrilha: boolean) {
    setDisciplinas((atuais) =>
      atuais.map((d) => (d.chave === disciplina ? { ...d, na_trilha: naTrilha } : d)),
    )
  }

  function mudarAssunto(disciplina: number, assunto: number, texto: string) {
    setDisciplinas((atuais) =>
      atuais.map((d) =>
        d.chave !== disciplina
          ? d
          : { ...d, assuntos: d.assuntos.map((a) => (a.chave === assunto ? { ...a, texto } : a)) },
      ),
    )
  }

  function removerAssunto(disciplina: number, assunto: number) {
    setDisciplinas((atuais) =>
      atuais.map((d) =>
        d.chave !== disciplina
          ? d
          : { ...d, assuntos: d.assuntos.filter((a) => a.chave !== assunto) },
      ),
    )
  }

  function acrescentar(evento: FormEvent, disciplina: number) {
    evento.preventDefault()
    const texto = (rascunhos[disciplina] ?? '').trim()
    if (!texto) return
    setDisciplinas((atuais) =>
      atuais.map((d) =>
        d.chave !== disciplina ? d : { ...d, assuntos: [...d.assuntos, { chave: nova(), texto }] },
      ),
    )
    setRascunhos((atuais) => ({ ...atuais, [disciplina]: '' }))
  }

  return (
    <div className="flex flex-col gap-6">
      {disciplinas.map((disciplina) => (
        <section
          key={disciplina.chave}
          aria-labelledby={`disciplina-${disciplina.chave}`}
          className="rounded-lg border border-border bg-card p-4 shadow-sm sm:p-6"
        >
          <header className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
            <h2
              id={`disciplina-${disciplina.chave}`}
              className="font-display text-lg font-bold text-foreground"
            >
              {disciplina.nome}
            </h2>
            <p className="text-sm text-muted-foreground">
              {[
                disciplina.periodo && `${disciplina.periodo}º período`,
                disciplina.carga_horaria && `${disciplina.carga_horaria} horas`,
              ]
                .filter(Boolean)
                .join(' · ')}
            </p>
            <label className="flex w-full items-center gap-2 text-sm font-semibold text-foreground">
              <Checkbox
                checked={disciplina.na_trilha}
                onCheckedChange={(marcada) => alternarTrilha(disciplina.chave, marcada === true)}
              />
              Incluir na trilha guiada
            </label>
          </header>

          {/* Num PPC são dezenas de disciplinas: as de fora mostram só o nome. */}
          {disciplina.na_trilha && (
            <>
              <ul className="flex flex-col gap-2">
                {disciplina.assuntos.map((assunto, i) => (
                  <li key={assunto.chave} className="flex items-center gap-2">
                    <Input
                      value={assunto.texto}
                      aria-label={`Assunto ${i + 1} de ${disciplina.nome}`}
                      maxLength={300}
                      onChange={(evento) =>
                        mudarAssunto(disciplina.chave, assunto.chave, evento.target.value)
                      }
                    />
                    <Situacao assunto={assunto} />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      aria-label={`Remover "${assunto.texto}"`}
                      onClick={() => removerAssunto(disciplina.chave, assunto.chave)}
                    >
                      <X />
                    </Button>
                  </li>
                ))}
              </ul>

              <form
                className="mt-3 flex items-center gap-2"
                onSubmit={(evento) => acrescentar(evento, disciplina.chave)}
              >
                <Input
                  placeholder="Acrescentar um assunto"
                  aria-label={`Novo assunto em ${disciplina.nome}`}
                  maxLength={300}
                  value={rascunhos[disciplina.chave] ?? ''}
                  onChange={(evento) =>
                    setRascunhos((atuais) => ({
                      ...atuais,
                      [disciplina.chave]: evento.target.value,
                    }))
                  }
                />
                <Button type="submit" variant="secondary" size="icon" aria-label="Acrescentar">
                  <Plus />
                </Button>
              </form>
            </>
          )}
        </section>
      ))}

      {erro != null && (
        <p role="alert" className="text-sm font-semibold text-destructive">
          {mensagemDeErro(erro)}
        </p>
      )}
      {vazia && (
        <p role="alert" className="text-sm font-semibold text-destructive">
          Inclua pelo menos uma disciplina, com um assunto, na trilha guiada.
        </p>
      )}

      <div className="flex flex-wrap justify-end gap-3">
        <Button
          variant="secondary"
          disabled={!alterada || vazia || salvando}
          onClick={() => aoSalvar(revisao)}
        >
          Salvar alterações
        </Button>
        <Button disabled={vazia || salvando} onClick={() => aoConfirmar(revisao, alterada)}>
          {salvando ? 'Salvando…' : 'Confirmar e gerar trilha'}
        </Button>
      </div>
    </div>
  )
}
