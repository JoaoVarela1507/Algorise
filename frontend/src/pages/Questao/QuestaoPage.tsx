import { ArrowLeft, Flag } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { AtividadeDoPasso } from '@/components/atividades/AtividadeDoPasso'
import { ModuloConcluido } from '@/components/atividades/ModuloConcluido'
import { PlayerYoutube } from '@/components/trilha/PlayerYoutube'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Carregando, ErroAoCarregar, Vazio } from '@/components/ui/estados'
import { useConcluirPasso, useReportarPasso } from '@/hooks/useAtividades'
import { useIniciarTrilha, usePasso } from '@/hooks/useTrilhas'
import { roteiroDaAtividade } from '@/lib/terminal/mapa'
import type { PassoConcluidoApi } from '@/services/atividades'

/**
 * As atividades de um passo da trilha (telas 28 a 33).
 *
 * O conteúdo vem da API (#29), que também decide se o passo está liberado —
 * pedir um passo bloqueado aqui responde 403, e a tela mostra o erro.
 *
 * Encadeia as atividades do passo, cada uma na tela do seu tipo (terminal,
 * múltipla escolha, ordenação, lacunas, resposta aberta, desafio), e fecha o
 * passo na API depois da última.
 */
export function QuestaoPage() {
  const { questaoId } = useParams()
  // Ao fechar um passo a tela navega para o seguinte, e a rota é a mesma: a
  // chave faz o React montar de novo, sem herdar a atividade e o "reportado"
  // do passo anterior.
  return <Passo key={questaoId} />
}

function Passo() {
  const { trilhaId, questaoId } = useParams()
  const navigate = useNavigate()
  const ordemPasso = Number(questaoId)

  const passo = usePasso(trilhaId, Number.isInteger(ordemPasso) ? ordemPasso : undefined)
  const concluir = useConcluirPasso(trilhaId)
  const reportar = useReportarPasso(trilhaId)
  const iniciar = useIniciarTrilha()
  const [escolhido, setEscolhido] = useState<number | null>(null)
  const inicio = useRef<number | null>(null)
  const [reportado, setReportado] = useState(false)
  // O que a API respondeu ao fechar o passo: enquanto existe, a comemoração
  // fica na tela. De lá o aluno volta ao mapa, com o polvo no módulo seguinte.
  const [concluido, setConcluido] = useState<PassoConcluidoApi | null>(null)
  const liberado = passo.isSuccess

  // Entrar num passo liberado é começar a trilha: é o que a põe no card
  // "trilha atual" da home. A API é idempotente, então repetir não estraga nada.
  useEffect(() => {
    if (trilhaId && liberado) iniciar.mutate(trilhaId)
    // `iniciar` muda de identidade a cada render; incluí-lo faria o efeito
    // disparar em loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trilhaId, liberado])

  if (passo.isPending) return <Carregando rotulo="Carregando atividade…" />
  if (passo.isError) {
    return <ErroAoCarregar erro={passo.error} aoTentarDeNovo={() => void passo.refetch()} />
  }

  const atividades = [...passo.data.atividades].sort((a, b) => a.ordem - b.ordem)
  // Retoma de onde o aluno parou: a primeira que ele ainda não acertou. Fica
  // gravado na primeira carga; senão, acertar uma atividade (que recarrega o
  // passo) pularia para a seguinte antes de o aluno clicar em Avançar.
  if (inicio.current === null) {
    const pendente = atividades.findIndex((atividade) => !atividade.concluida)
    inicio.current = pendente >= 0 ? pendente : 0
  }
  const indice = escolhido ?? inicio.current
  const atual = atividades[indice]
  const ordem = passo.data.ordem

  // Fecha na API, que paga o bônus e diz qual é o próximo, e comemora. Se ela
  // recusar (atividade pendente), volta para a trilha — lá o aluno vê o que falta.
  async function fecharPasso() {
    try {
      setConcluido(await concluir.mutateAsync(ordem))
    } catch {
      navigate(`/trilhas/${trilhaId}`)
    }
  }

  function reportarVideo() {
    reportar.mutate(ordem, {
      // Com reportes suficientes o módulo saiu da trilha: não há mais o que ver aqui.
      onSuccess: (resultado) =>
        resultado.removido ? navigate(`/trilhas/${trilhaId}`) : setReportado(true),
    })
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
      <header className="flex flex-col gap-1">
        <Link
          to={`/trilhas/${trilhaId}`}
          className="flex w-fit items-center gap-1 text-sm font-semibold text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" aria-hidden />
          {passo.data.trilha_nome}
        </Link>
        <h1 className="font-display text-2xl font-bold text-foreground">{passo.data.titulo}</h1>
      </header>

      {passo.data.video_url && (
        <section aria-label="Vídeo do passo" className="flex flex-col gap-2">
          <PlayerYoutube
            url={passo.data.video_url}
            titulo={passo.data.titulo}
            inicio={passo.data.inicio_segundos}
            fim={passo.data.fim_segundos}
          />
          {passo.data.origem === 'youtube' && (
            <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground">
              <span className="flex items-center gap-2">
                <Badge variant="secondary">Gerado automaticamente</Badge>
                {passo.data.canal && <span>Vídeo de {passo.data.canal}</span>}
              </span>
              {reportado ? (
                <span role="status">Obrigado! Vamos revisar este vídeo.</span>
              ) : (
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={reportar.isPending}
                  onClick={reportarVideo}
                >
                  <Flag aria-hidden />
                  Reportar vídeo
                </Button>
              )}
            </div>
          )}
        </section>
      )}

      {atual ? (
        <AtividadeDoPasso
          // A chave troca junto com a atividade: sem ela, a resposta (ou o
          // terminal) da anterior continuaria na tela.
          key={atual.id}
          atividade={atual}
          roteiro={roteiroDaAtividade(passo.data.trilha_slug, ordem, atual.ordem)}
          numero={indice + 1}
          total={atividades.length}
          aoAvancar={() => {
            if (indice + 1 < atividades.length) {
              setEscolhido(indice + 1)
              return
            }
            void fecharPasso()
          }}
        />
      ) : passo.data.video_url ? (
        // O passo feito de um vídeo (#210) ainda não tem atividade: assistir é o passo.
        <div className="flex justify-end">
          <Button disabled={concluir.isPending} onClick={() => void fecharPasso()}>
            Concluir passo
          </Button>
        </div>
      ) : (
        // Sem atividade não há o que travar: a API fecha o passo, e o aluno
        // não fica preso num módulo que ainda não ganhou conteúdo.
        <Vazio
          titulo="Este módulo ainda não tem atividades"
          descricao="Pode seguir: o conteúdo dele chega em breve."
          acao={
            <Button disabled={concluir.isPending} onClick={() => void fecharPasso()}>
              Concluir e seguir
            </Button>
          }
        />
      )}

      {concluido && (
        <ModuloConcluido
          titulo={passo.data.titulo}
          xpGanho={concluido.xp_ganho}
          proximo={concluido.proximo ?? null}
          // De volta ao mapa: o detalhe da trilha já foi invalidado ao concluir,
          // então o polvo aparece no módulo que acabou de abrir.
          aoContinuar={() => navigate(`/trilhas/${trilhaId}`)}
        />
      )}
    </div>
  )
}
