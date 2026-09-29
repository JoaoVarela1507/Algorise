import { useState, type FormEvent } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { BookOpen, CalendarDays, GraduationCap, Pencil } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { toast } from '@/components/ui/toaster'
import { useAuth } from '@/contexts/AuthContext'
import type { Usuario } from '@/types/usuario'

const periodos = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

function Linha({
  icone: Icone,
  rotulo,
  valor,
}: {
  icone: typeof BookOpen
  rotulo: string
  valor?: string
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg bg-secondary/50 px-4 py-3">
      <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary">
        <Icone className="size-5" aria-hidden />
      </span>
      <div className="min-w-0">
        <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">{rotulo}</p>
        <p
          className={
            valor ? 'truncate font-semibold text-foreground' : 'italic text-muted-foreground'
          }
        >
          {valor ?? 'Não informado'}
        </p>
      </div>
    </div>
  )
}

export function DadosAcademicosCard({ usuario }: { usuario: Usuario }) {
  const { atualizarPerfil } = useAuth()
  const [editando, setEditando] = useState(false)
  const [salvando, setSalvando] = useState(false)
  const [instituicao, setInstituicao] = useState(usuario.instituicao ?? '')
  const [curso, setCurso] = useState(usuario.curso ?? '')
  const [periodo, setPeriodo] = useState(usuario.periodo ? String(usuario.periodo) : '')

  function abrirEdicao() {
    setInstituicao(usuario.instituicao ?? '')
    setCurso(usuario.curso ?? '')
    setPeriodo(usuario.periodo ? String(usuario.periodo) : '')
    setEditando(true)
  }

  async function salvar(event: FormEvent) {
    event.preventDefault()
    setSalvando(true)
    try {
      await atualizarPerfil({
        instituicao: instituicao.trim() || undefined,
        curso: curso.trim() || undefined,
        periodo: periodo ? Number(periodo) : undefined,
      })
      toast.success('Dados acadêmicos atualizados')
      setEditando(false)
    } catch (erro) {
      toast.error(erro instanceof Error ? erro.message : 'Não foi possível salvar.')
    } finally {
      setSalvando(false)
    }
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-border bg-card p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between gap-2">
        <h2 className="font-display text-lg font-bold text-foreground">Dados acadêmicos</h2>
        {!editando && (
          <Button variant="ghost" size="sm" onClick={abrirEdicao}>
            <Pencil className="!size-4" />
            Editar
          </Button>
        )}
      </div>

      <AnimatePresence mode="wait" initial={false}>
        {editando ? (
          <motion.form
            key="form"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            onSubmit={salvar}
            className="flex flex-1 flex-col gap-4"
          >
            <div className="flex flex-col gap-1">
              <Label htmlFor="perfil-instituicao">Universidade/faculdade</Label>
              <Input
                id="perfil-instituicao"
                value={instituicao}
                onChange={(event) => setInstituicao(event.target.value)}
                placeholder="Informe sua instituição de ensino"
                autoFocus
              />
            </div>
            <div className="flex flex-col gap-1">
              <Label htmlFor="perfil-curso">Curso de graduação</Label>
              <Input
                id="perfil-curso"
                value={curso}
                onChange={(event) => setCurso(event.target.value)}
                placeholder="Informe o seu curso"
              />
            </div>
            <div className="flex flex-col gap-1">
              <Label htmlFor="perfil-periodo">Período atual</Label>
              <Select value={periodo} onValueChange={setPeriodo}>
                <SelectTrigger id="perfil-periodo">
                  <SelectValue placeholder="Selecione o período" />
                </SelectTrigger>
                <SelectContent>
                  {periodos.map((p) => (
                    <SelectItem key={p} value={String(p)}>
                      {p}º período
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="mt-auto flex gap-2 pt-2">
              <Button
                type="button"
                variant="ghost"
                className="flex-1"
                onClick={() => setEditando(false)}
              >
                Cancelar
              </Button>
              <Button type="submit" className="flex-1" disabled={salvando}>
                {salvando ? 'Salvando…' : 'Salvar'}
              </Button>
            </div>
          </motion.form>
        ) : (
          <motion.div
            key="leitura"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="flex flex-1 flex-col gap-3"
          >
            <Linha icone={GraduationCap} rotulo="Instituição" valor={usuario.instituicao} />
            <Linha icone={BookOpen} rotulo="Curso" valor={usuario.curso} />
            <Linha
              icone={CalendarDays}
              rotulo="Período"
              valor={usuario.periodo ? `${usuario.periodo}º período` : undefined}
            />
            {!usuario.instituicao && (
              <p className="mt-auto rounded-lg border border-dashed border-primary/40 bg-primary/5 p-3 text-sm text-muted-foreground">
                Complete seus dados para o Algorise montar as trilhas a partir da sua ementa.
              </p>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
