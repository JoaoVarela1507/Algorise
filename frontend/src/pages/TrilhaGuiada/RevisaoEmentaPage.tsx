import { Link, useNavigate } from 'react-router-dom'
import { RevisaoAssuntos } from '@/components/trilha-guiada/RevisaoAssuntos'
import { Button } from '@/components/ui/button'
import { Carregando, ErroAoCarregar, Vazio } from '@/components/ui/estados'
import {
  useAssuntos,
  useConfirmarEmenta,
  useEmentaAtual,
  useRelerAssuntos,
  useRevisarAssuntos,
} from '@/hooks/useEmenta'
import { ApiError } from '@/services/api'
import { emLeitura, type DisciplinaRevisada } from '@/services/ementa'

/**
 * Revisão dos assuntos lidos da ementa, antes de gerar a trilha guiada (#38).
 *
 * Abre logo depois do onboarding guiado: a leitura ainda pode estar rodando no
 * servidor, e a página espera por ela.
 */
export function RevisaoEmentaPage() {
  const navigate = useNavigate()
  const ementa = useEmentaAtual()
  const assuntos = useAssuntos(ementa.data)
  const id = ementa.data?.id ?? 0
  const revisar = useRevisarAssuntos(id)
  const confirmar = useConfirmarEmenta(id)
  const reler = useRelerAssuntos(id)

  async function confirmarRevisao(disciplinas: DisciplinaRevisada[], alterada: boolean) {
    try {
      if (alterada) await revisar.mutateAsync(disciplinas)
      await confirmar.mutateAsync()
    } catch {
      // O erro já está na mutation, e a tela o mostra.
      return
    }
    navigate('/trilha-guiada')
  }

  let conteudo
  if (ementa.isPending) {
    conteudo = <Carregando rotulo="Buscando sua ementa…" />
  } else if (ementa.isError) {
    conteudo =
      ementa.error instanceof ApiError && ementa.error.status === 404 ? (
        <Vazio
          titulo="Você ainda não enviou uma ementa"
          descricao="A trilha guiada parte da ementa do seu curso. Envie o PDF no último passo do onboarding."
          acao={
            <Button asChild variant="secondary">
              <Link to="/onboarding">Enviar a ementa</Link>
            </Button>
          }
        />
      ) : (
        <ErroAoCarregar erro={ementa.error} aoTentarDeNovo={() => void ementa.refetch()} />
      )
  } else if (ementa.data.status === 'falhou') {
    conteudo = (
      <Vazio
        titulo="Não conseguimos ler o PDF"
        descricao={ementa.data.erro ?? undefined}
        acao={
          <Button asChild variant="secondary">
            <Link to="/onboarding">Enviar outra ementa</Link>
          </Button>
        }
      />
    )
  } else if (emLeitura(ementa.data)) {
    conteudo = (
      <Carregando rotulo="Lendo sua ementa… isso pode levar um minuto." className="py-20" />
    )
  } else if (ementa.data.status_assuntos === 'falhou') {
    conteudo = (
      <Vazio
        titulo="Não deu para ler os assuntos"
        descricao={ementa.data.erro_assuntos ?? undefined}
        acao={
          <Button variant="secondary" disabled={reler.isPending} onClick={() => reler.mutate()}>
            Tentar de novo
          </Button>
        }
      />
    )
  } else if (assuntos.isPending) {
    conteudo = <Carregando rotulo="Carregando os assuntos…" />
  } else if (assuntos.isError) {
    conteudo = (
      <ErroAoCarregar erro={assuntos.error} aoTentarDeNovo={() => void assuntos.refetch()} />
    )
  } else {
    conteudo = (
      <RevisaoAssuntos
        // Recria o formulário com o que o servidor devolveu depois de salvar.
        key={assuntos.dataUpdatedAt}
        disciplinas={assuntos.data.disciplinas}
        salvando={revisar.isPending || confirmar.isPending}
        erro={revisar.error ?? confirmar.error}
        aoSalvar={(disciplinas) => revisar.mutate(disciplinas)}
        aoConfirmar={(disciplinas, alterada) => void confirmarRevisao(disciplinas, alterada)}
      />
    )
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
      <header>
        <h1 className="font-display text-3xl font-bold text-foreground">Revise sua ementa</h1>
        <p className="text-muted-foreground">
          Estes são os assuntos que encontramos. Corrija, remova ou acrescente o que faltar: a sua
          trilha guiada sai desta lista.
        </p>
      </header>
      {conteudo}
    </div>
  )
}
