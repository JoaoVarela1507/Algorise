import { useEffect, useState } from 'react'
import { Code2, FlaskConical, Lightbulb, Play, X } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'
import { EditorDeCodigo } from '@/components/desafio/EditorDeCodigo'
import { ResultadoDoDesafio } from '@/components/desafio/ResultadoDoDesafio'
import { Button } from '@/components/ui/button'
import { Carregando, ErroAoCarregar, Vazio } from '@/components/ui/estados'
import { LogoLoader } from '@/components/ui/logo-loader'
import { useDesafio, useVerificarDesafio } from '@/hooks/useDesafio'
import { useTrilha } from '@/hooks/useTrilhas'
import { ApiError } from '@/services/api'

/**
 * Desafio proposto da trilha (tela 40, #25): o programa que fecha a trilha,
 * escrito no editor e corrigido no servidor contra os casos de teste.
 *
 * O desafio é a atividade `desafio-codigo` da trilha. Ele aparece depois de
 * concluir todos os passos (a tela da trilha final mostra o botão), e não
 * dentro do passo: no protótipo ele é o fechamento, não mais uma atividade.
 */
export function DesafioPage() {
  const { trilhaId } = useParams()
  const navigate = useNavigate()
  const trilha = useTrilha(trilhaId)

  if (trilha.isPending) return <Carregando rotulo="Carregando desafio…" />
  if (trilha.isError) {
    return <ErroAoCarregar erro={trilha.error} aoTentarDeNovo={() => void trilha.refetch()} />
  }

  const desafio = trilha.data.modulos
    ?.flatMap((modulo) => modulo.atividades ?? [])
    .find((atividade) => atividade.tipo === 'desafio-codigo')

  if (!desafio) {
    return (
      <Vazio
        titulo="Esta trilha não tem desafio"
        descricao="Escolha outra trilha para continuar praticando."
        acao={<Button onClick={() => navigate('/trilhas')}>Ver trilhas</Button>}
      />
    )
  }

  return (
    <Desafio
      key={desafio.id}
      desafioId={desafio.id}
      jaFeito={Boolean(desafio.concluida)}
      trilhaNome={trilha.data.nome}
      aoFechar={() => navigate(`/trilhas/${trilhaId}`)}
      aoVoltarParaTrilhas={() => navigate('/trilhas')}
    />
  )
}

/** Rascunho por desafio: sair da tela e voltar não perde o código. */
function chaveDoRascunho(id: number) {
  return `algorise:desafio:${id}`
}

function lerRascunho(id: number): string {
  try {
    return localStorage.getItem(chaveDoRascunho(id)) ?? ''
  } catch {
    return ''
  }
}

function Desafio({
  desafioId,
  jaFeito,
  trilhaNome,
  aoFechar,
  aoVoltarParaTrilhas,
}: {
  desafioId: number
  jaFeito: boolean
  trilhaNome: string
  aoFechar: () => void
  aoVoltarParaTrilhas: () => void
}) {
  const consulta = useDesafio(desafioId)
  const { verificar, limpar, rodando, resultado, erroDoEnvio } = useVerificarDesafio(desafioId)
  const [codigo, setCodigo] = useState(() => lerRascunho(desafioId))
  const [verDica, setVerDica] = useState(false)
  // Se já estava feito quando a tela abriu: o novo acerto não paga XP de novo.
  const [feitoAntes] = useState(jaFeito)

  useEffect(() => {
    try {
      localStorage.setItem(chaveDoRascunho(desafioId), codigo)
    } catch {
      // Sem storage, o rascunho só não sobrevive a sair da tela.
    }
  }, [desafioId, codigo])

  if (consulta.isPending) return <Carregando rotulo="Carregando desafio…" />
  if (consulta.isError) {
    return <ErroAoCarregar erro={consulta.error} aoTentarDeNovo={() => void consulta.refetch()} />
  }
  const desafio = consulta.data
  const ocultos = desafio.total_casos - desafio.casos_publicos.length

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-5">
      <header className="flex items-start gap-3">
        <Button
          variant="ghost"
          size="icon"
          className="-ml-2 shrink-0"
          aria-label={`Fechar e voltar para ${trilhaNome}`}
          onClick={aoFechar}
        >
          <X />
        </Button>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-muted-foreground">{trilhaNome}</p>
          <h1 className="flex items-center gap-2 font-display text-2xl font-bold text-foreground">
            <Code2 className="size-6 shrink-0 text-primary" aria-hidden />
            Desafio proposto
          </h1>
        </div>
      </header>

      <section className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4 shadow-sm sm:p-5">
        <p className="font-display text-lg font-bold text-foreground">{desafio.enunciado}</p>
        {desafio.dica && (
          <div>
            <Button
              variant="ghost"
              size="sm"
              className="-ml-2"
              onClick={() => setVerDica(!verDica)}
            >
              <Lightbulb className="size-4" aria-hidden />
              {verDica ? 'Esconder dica' : 'Ver dica'}
            </Button>
            {verDica && <p className="mt-1 text-sm text-muted-foreground">{desafio.dica}</p>}
          </div>
        )}
        {desafio.casos_publicos.map((caso) => (
          <div
            key={caso.ordem}
            className="grid grid-cols-[minmax(0,1fr)] gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]"
          >
            <Exemplo titulo="Exemplo de entrada" texto={caso.entrada} />
            <Exemplo titulo="Saída esperada" texto={caso.saida_esperada} />
          </div>
        ))}
      </section>

      <section className="flex flex-col gap-3" aria-label="Seu código">
        <EditorDeCodigo
          valor={codigo}
          aoMudar={setCodigo}
          rotulo="Seu código em Python"
          desabilitado={rodando}
        />

        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <FlaskConical className="size-4" aria-hidden />
            {desafio.total_casos} {desafio.total_casos === 1 ? 'caso de teste' : 'casos de teste'}
            {ocultos > 0 && ` (${ocultos} ${ocultos === 1 ? 'oculto' : 'ocultos'})`}
            {' · '}+{desafio.xp} XP
          </p>
          <Button size="lg" disabled={!codigo.trim() || rodando} onClick={() => verificar(codigo)}>
            <Play />
            Verificar
          </Button>
        </div>

        {rodando && (
          <div
            role="status"
            className="flex items-center gap-3 rounded-xl border border-border bg-card p-3"
          >
            <LogoLoader tamanho="sm" />
            <p className="text-sm font-semibold text-muted-foreground">
              O polvo está testando seu código…
            </p>
          </div>
        )}
        {erroDoEnvio && !rodando && (
          <p role="alert" className="text-sm font-semibold text-destructive">
            {erroDoEnvio instanceof ApiError
              ? erroDoEnvio.message
              : 'Não deu para enviar seu código. Tente de novo.'}
          </p>
        )}
      </section>

      {resultado && (
        <ResultadoDoDesafio
          execucao={resultado}
          xp={desafio.xp}
          jaTinhaFeito={feitoAntes}
          aoTentarDeNovo={limpar}
          aoVoltarParaTrilhas={aoVoltarParaTrilhas}
        />
      )}
    </div>
  )
}

function Exemplo({ titulo, texto }: { titulo: string; texto: string }) {
  return (
    <div>
      <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">{titulo}</p>
      <pre className="mt-1 overflow-x-auto rounded-lg bg-muted p-3 font-mono text-sm text-foreground">
        {/* A linha vazia do fim é o "Enter" que encerra a entrada: fica visível. */}
        {texto.replace(/\n$/, '').replace(/^$/gm, '⏎') || '(vazio)'}
      </pre>
    </div>
  )
}
