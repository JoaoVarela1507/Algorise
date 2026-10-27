import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { CircleCheck, Upload } from 'lucide-react'
import { CampoAutocomplete } from '@/components/onboarding/CampoAutocomplete'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { niveis, trilhas, type OpcaoPerfil } from '@/components/onboarding/opcoes'
import { cn } from '@/lib/utils'
import { useAuth } from '@/contexts/AuthContext'
import { useCursos, useInstituicoes } from '@/hooks/useAcademico'
import { enviarEmenta, type Escolha } from '@/services/onboarding'
import type { NivelExperiencia, TipoTrilha } from '@/types/usuario'

const periodos = [1, 2, 3, 4, 5, 6, 7, 8] as const

function EtapaSelecao<T extends string>({
  opcoes,
  selecionado,
  onSelecionar,
}: {
  opcoes: OpcaoPerfil<T>[]
  selecionado: T | null
  onSelecionar: (valor: T) => void
}) {
  return (
    <div className="flex flex-col gap-3">
      {opcoes.map((opcao) => {
        const selecionadoAtual = selecionado === opcao.valor
        return (
          <button
            key={opcao.valor}
            type="button"
            onClick={() => onSelecionar(opcao.valor)}
            aria-pressed={selecionadoAtual}
            className={cn(
              'flex items-start gap-4 rounded-lg border-2 p-4 text-left transition-colors',
              selecionadoAtual
                ? 'border-primary bg-primary/10'
                : 'border-border hover:border-primary/50',
            )}
          >
            <span
              className={cn(
                'flex size-11 shrink-0 items-center justify-center rounded-full transition-colors',
                selecionadoAtual ? 'bg-primary text-primary-foreground' : 'bg-accent text-primary',
              )}
            >
              <opcao.icone className="size-5" />
            </span>
            <div className="flex flex-col gap-1 pt-1">
              <span className="font-display font-bold text-foreground">{opcao.titulo}</span>
              <span className="text-sm text-muted-foreground">{opcao.descricao}</span>
            </div>
          </button>
        )
      })}
    </div>
  )
}

export interface RascunhoOnboarding {
  passo: number
  nivel: NivelExperiencia | null
  trilha: TipoTrilha | null
  instituicao: Escolha
  curso: Escolha
  periodo: string
  ementa: File | null
}

/**
 * Passos de nível + trilha + dados da instituição para completar o cadastro.
 * Usado tanto na rota /onboarding quanto embutido na BoasVindasPage.
 *
 * Aceita um rascunho controlado de fora para sobreviver a idas e vindas (ex.:
 * voltar pro cadastro e retornar) sem perder o que já foi preenchido.
 */
export function OnboardingWizard({
  onConcluir,
  onVoltarInicio,
  rascunho,
  onRascunhoChange,
}: {
  onConcluir?: () => void
  onVoltarInicio?: () => void
  rascunho?: RascunhoOnboarding
  onRascunhoChange?: (rascunho: RascunhoOnboarding) => void
}) {
  const { usuario, concluirOnboarding } = useAuth()
  const [salvando, setSalvando] = useState(false)
  const [erroApi, setErroApi] = useState<string | null>(null)
  const navigate = useNavigate()

  const [passo, setPasso] = useState(rascunho?.passo ?? 1)
  const [nivel, setNivel] = useState<NivelExperiencia | null>(
    rascunho?.nivel ?? usuario?.nivelExperiencia ?? null,
  )
  const [trilha, setTrilha] = useState<TipoTrilha | null>(
    rascunho?.trilha ?? usuario?.tipoTrilha ?? null,
  )
  const [instituicao, setInstituicao] = useState<Escolha>(
    rascunho?.instituicao ?? { texto: '', id: null },
  )
  const [curso, setCurso] = useState<Escolha>(rascunho?.curso ?? { texto: '', id: null })
  // A ementa já subiu: tentar de novo depois de um erro não a envia duas vezes.
  const [ementaEnviada, setEmentaEnviada] = useState<File | null>(null)

  const instituicoes = useInstituicoes(instituicao.id === null ? instituicao.texto : '')
  const cursos = useCursos(instituicao.id)
  const textoDoCurso = curso.texto.trim().toLowerCase()
  const sugestoesDeCurso = (cursos.data ?? [])
    .filter((c) => c.nome.toLowerCase().includes(textoDoCurso))
    .map((c) => ({ id: c.id, rotulo: c.nome }))
  const [periodo, setPeriodo] = useState(rascunho?.periodo ?? '')
  const [ementa, setEmenta] = useState<File | null>(rascunho?.ementa ?? null)

  useEffect(() => {
    onRascunhoChange?.({ passo, nivel, trilha, instituicao, curso, periodo, ementa })
  }, [passo, nivel, trilha, instituicao, curso, periodo, ementa, onRascunhoChange])

  // Na trilha guiada o plano de estudos parte da ementa, então o upload é
  // obrigatório; nas outras duas (livre e mista) é só um extra opcional.
  const ementaObrigatoria = trilha === 'guiada'

  async function finalizar() {
    // Os passos 1 e 2 só deixam avançar com os dois escolhidos.
    if (!nivel || !trilha) return
    setSalvando(true)
    setErroApi(null)
    try {
      await concluirOnboarding({
        nivelExperiencia: nivel,
        tipoTrilha: trilha,
        instituicao,
        curso,
        periodo: periodo ? Number(periodo) : undefined,
      })
    } catch (erro) {
      setErroApi(erro instanceof Error ? erro.message : 'Não foi possível salvar.')
      setSalvando(false)
      return
    }

    // Depois do onboarding, para a ementa já sair com o curso e o período do
    // aluno. O texto é lido no servidor, sem o aluno esperar.
    if (ementa && ementa !== ementaEnviada) {
      try {
        await enviarEmenta(ementa)
        setEmentaEnviada(ementa)
      } catch (erro) {
        const motivo = erro instanceof Error ? erro.message : 'Tente outro arquivo.'
        setErroApi(`Seus dados foram salvos, mas a ementa não foi enviada: ${motivo}`)
        setSalvando(false)
        return
      }
    }
    setSalvando(false)
    if (onConcluir) {
      onConcluir()
    } else {
      navigate('/')
    }
  }

  return (
    <div>
      <p className="mb-1 text-center text-sm font-semibold text-muted-foreground">
        Passo {passo} de 3
      </p>
      <h1 className="mb-6 text-center font-display text-xl font-bold text-foreground">
        Ajude-nos a identificar seu caminho de aprendizagem
      </h1>

      <AnimatePresence mode="wait">
        <motion.div
          key={passo}
          initial={{ opacity: 0, x: 16 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -16 }}
          transition={{ duration: 0.25 }}
          className="h-[35rem]"
        >
          {passo === 1 && (
            <div className="flex h-full flex-col gap-6">
              <p className="text-center text-foreground">Qual é o seu nível em programação?</p>
              <EtapaSelecao opcoes={niveis} selecionado={nivel} onSelecionar={setNivel} />
              {onVoltarInicio ? (
                <div className="mt-auto flex gap-3">
                  <Button variant="ghost" size="lg" onClick={onVoltarInicio}>
                    Voltar
                  </Button>
                  <Button
                    className="flex-1"
                    size="lg"
                    disabled={!nivel}
                    onClick={() => setPasso(2)}
                  >
                    Continuar
                  </Button>
                </div>
              ) : (
                <Button
                  full
                  size="lg"
                  className="mt-auto"
                  disabled={!nivel}
                  onClick={() => setPasso(2)}
                >
                  Continuar
                </Button>
              )}
            </div>
          )}

          {passo === 2 && (
            <div className="flex h-full flex-col gap-6">
              <p className="text-center text-foreground">
                Você pretende utilizar uma trilha livre ou guiada para a sua faculdade?
              </p>
              <EtapaSelecao opcoes={trilhas} selecionado={trilha} onSelecionar={setTrilha} />
              <div className="mt-auto flex gap-3">
                <Button variant="ghost" size="lg" onClick={() => setPasso(1)}>
                  Voltar
                </Button>
                <Button className="flex-1" size="lg" disabled={!trilha} onClick={() => setPasso(3)}>
                  Continuar
                </Button>
              </div>
            </div>
          )}

          {passo === 3 && (
            <div className="flex h-full flex-col gap-4">
              <p className="text-center text-foreground">
                Trilha {trilhas.find((t) => t.valor === trilha)?.titulo}
              </p>

              <label
                htmlFor="grade-curricular"
                className={cn(
                  'flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed p-6 text-center text-sm transition-colors',
                  ementa
                    ? 'border-primary/50 text-foreground'
                    : 'border-border text-muted-foreground hover:border-primary/50',
                )}
              >
                {ementa ? (
                  <CircleCheck className="size-6 text-primary" />
                ) : (
                  <Upload className="size-6" />
                )}
                {ementa ? ementa.name : 'Faça o upload da sua grade curricular'}
                <span className="text-xs">
                  {ementaObrigatoria
                    ? 'PDF de até 5 MB (obrigatório)'
                    : 'PDF de até 5 MB (opcional)'}
                </span>
                <input
                  id="grade-curricular"
                  type="file"
                  className="hidden"
                  accept="application/pdf"
                  onChange={(event) => setEmenta(event.target.files?.[0] ?? null)}
                />
              </label>

              <CampoAutocomplete
                id="instituicao"
                rotulo="Qual é a sua universidade/faculdade?"
                placeholder="Informe sua instituição de ensino"
                valor={instituicao}
                onChange={(nova) => {
                  // Curso é da instituição: trocar uma invalida o curso escolhido.
                  if (nova.id !== instituicao.id) setCurso((atual) => ({ ...atual, id: null }))
                  setInstituicao(nova)
                }}
                carregando={instituicoes.isFetching}
                sugestoes={(instituicoes.data ?? []).map((i) => ({
                  id: i.id,
                  rotulo: i.nome,
                  detalhe: i.sigla ?? undefined,
                }))}
              />

              <CampoAutocomplete
                id="curso"
                rotulo="Qual é o seu curso de graduação?"
                placeholder="Informe o seu curso"
                valor={curso}
                onChange={setCurso}
                carregando={cursos.isFetching}
                sugestoes={sugestoesDeCurso}
              />

              <div className="flex flex-col gap-1">
                <Label htmlFor="periodo">Selecione seu período/semestre atual</Label>
                <Select value={periodo} onValueChange={setPeriodo}>
                  <SelectTrigger id="periodo" aria-label="Período">
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

              {erroApi && (
                <p role="alert" className="text-sm font-semibold text-destructive">
                  {erroApi}
                </p>
              )}

              <div className="mt-auto flex gap-3">
                <Button variant="ghost" size="lg" onClick={() => setPasso(2)}>
                  Voltar
                </Button>
                <Button
                  className="flex-1"
                  size="lg"
                  disabled={!instituicao.texto.trim() || (ementaObrigatoria && !ementa) || salvando}
                  onClick={finalizar}
                >
                  {salvando ? 'Salvando…' : 'Continuar'}
                </Button>
              </div>
            </div>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
