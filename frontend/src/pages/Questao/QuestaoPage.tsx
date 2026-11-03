import { ArrowLeft, Flag } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { AtividadeTerminal } from '@/components/atividades/AtividadeTerminal'
import { PlayerYoutube } from '@/components/trilha/PlayerYoutube'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Carregando, ErroAoCarregar, Vazio } from '@/components/ui/estados'
import { useConcluirPasso, useReportarPasso } from '@/hooks/useAtividades'
import { usePasso } from '@/hooks/useTrilhas'
import { roteiroDaAtividade } from '@/lib/terminal/mapa'

/**
 * As atividades de um passo da trilha (telas 28 a 33).
 *
 * O conteúdo vem da API (#29), que também decide se o passo está liberado —
 * pedir um passo bloqueado aqui responde 403, e a tela mostra o erro.
 *
 * O acabamento visual das telas 28 a 38 é a #22. Esta versão é funcional: ela
 * encadeia as atividades de terminal do passo e deixa o fluxo completo de ponta
 * a ponta.
 */
export function QuestaoPage() {
  const { trilhaId, questaoId } = useParams()
  const navigate = useNavigate()
  const ordemPasso = Number(questaoId)

  const passo = usePasso(trilhaId, Number.isInteger(ordemPasso) ? ordemPasso : undefined)
  const concluir = useConcluirPasso(trilhaId)
  const reportar = useReportarPasso(trilhaId)
  const [indice, setIndice] = useState(0)
  const [reportado, setReportado] = useState(false)

  if (passo.isPending) return <Carregando rotulo="Carregando atividade…" />
  if (passo.isError) {
    return <ErroAoCarregar erro={passo.error} aoTentarDeNovo={() => void passo.refetch()} />
  }

  // Só as atividades de terminal: as de resposta aberta e as demais chegam com
  // as telas delas (#22) e com a correção por IA (#30).
  const atividades = passo.data.atividades
    .map((atividade) => ({
      ...atividade,
      roteiro: roteiroDaAtividade(passo.data.trilha_slug, passo.data.ordem, atividade.ordem),
    }))
    .filter((atividade) => atividade.roteiro !== null)

  const atual = atividades[indice]
  const ordem = passo.data.ordem

  // Fecha na API, que paga o bônus e diz qual é o próximo. Se ela recusar
  // (atividade pendente), volta para a trilha — lá o aluno vê o que falta.
  async function fecharPasso() {
    try {
      const resultado = await concluir.mutateAsync(ordem)
      navigate(
        resultado.proximo
          ? `/trilhas/${trilhaId}/questao/${resultado.proximo}`
          : `/trilhas/${trilhaId}`,
      )
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
        <AtividadeTerminal
          // A chave troca junto com a atividade: sem ela, o terminal da
          // anterior continuaria na tela com o histórico dela.
          key={atual.id}
          atividadeId={atual.id}
          enunciado={atual.enunciado}
          dica={atual.dica}
          atividade={atual.roteiro!}
          numero={indice + 1}
          total={atividades.length}
          tempoSugeridoSegundos={atual.tempo_sugerido_segundos}
          aoAvancar={async () => {
            if (indice + 1 < atividades.length) {
              setIndice(indice + 1)
              return
            }
            await fecharPasso()
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
        <Vazio
          titulo="Nada para fazer por aqui ainda"
          descricao="Este passo não tem atividade de terminal."
          acao={
            <Button variant="secondary" onClick={() => navigate(`/trilhas/${trilhaId}`)}>
              Voltar para a trilha
            </Button>
          }
        />
      )}
    </div>
  )
}
