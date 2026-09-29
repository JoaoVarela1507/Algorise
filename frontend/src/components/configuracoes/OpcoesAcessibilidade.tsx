import { Opcao } from '@/components/configuracoes/Secao'
import { Segmentado } from '@/components/perfil/Segmentado'
import { useAccessibility } from '@/contexts/AccessibilityContext'

const simNao = [
  { valor: 'sim', rotulo: 'Sim' },
  { valor: 'nao', rotulo: 'Não' },
] as const

/** Tamanho da fonte, alto contraste e animações. Usado no Perfil e nas Configurações. */
export function OpcoesAcessibilidade() {
  const {
    tamanhoFonte,
    altoContraste,
    reduzirAnimacoes,
    setTamanhoFonte,
    setAltoContraste,
    setReduzirAnimacoes,
  } = useAccessibility()

  return (
    <>
      <Opcao titulo="Tamanho da fonte" descricao="Aumenta todo o texto do app.">
        <Segmentado
          rotulo="Tamanho da fonte"
          opcoes={[
            { valor: 'normal', rotulo: 'Normal' },
            { valor: 'alta', rotulo: 'Alta' },
          ]}
          valor={tamanhoFonte}
          onChange={setTamanhoFonte}
        />
      </Opcao>
      <Opcao titulo="Fundo de alto contraste" descricao="Cores mais fortes para leitura.">
        <Segmentado
          rotulo="Fundo de alto contraste"
          opcoes={[...simNao]}
          valor={altoContraste ? 'sim' : 'nao'}
          onChange={(valor) => setAltoContraste(valor === 'sim')}
        />
      </Opcao>
      <Opcao titulo="Reduzir animações" descricao="Desliga movimentos e transições.">
        <Segmentado
          rotulo="Reduzir animações"
          opcoes={[...simNao]}
          valor={reduzirAnimacoes ? 'sim' : 'nao'}
          onChange={(valor) => setReduzirAnimacoes(valor === 'sim')}
        />
      </Opcao>
    </>
  )
}
