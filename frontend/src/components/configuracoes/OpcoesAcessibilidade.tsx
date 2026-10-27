import { Opcao } from '@/components/configuracoes/Secao'
import { Segmentado } from '@/components/perfil/Segmentado'
import { toast } from '@/components/ui/toaster'
import { useAccessibility } from '@/contexts/AccessibilityContext'
import { useAuth } from '@/contexts/AuthContext'
import type { Preferencias } from '@/types/usuario'

const simNao = [
  { valor: 'sim', rotulo: 'Sim' },
  { valor: 'nao', rotulo: 'Não' },
] as const

/**
 * Tamanho da fonte, alto contraste e animações. Usado no Perfil e nas Configurações.
 *
 * A mudança vale na hora neste navegador e segue para a conta em seguida, para
 * o aluno encontrá-la em outro aparelho. Se a API falhar, a tela não volta
 * atrás: a preferência já está valendo aqui, só não foi para a conta.
 */
export function OpcoesAcessibilidade() {
  const {
    tamanhoFonte,
    altoContraste,
    reduzirAnimacoes,
    setTamanhoFonte,
    setAltoContraste,
    setReduzirAnimacoes,
  } = useAccessibility()
  const { usuario, salvarPreferencias } = useAuth()

  function levarParaConta(dados: Partial<Preferencias>) {
    if (!usuario) return
    salvarPreferencias(dados).catch(() =>
      toast.error('Não foi possível salvar a preferência na sua conta.'),
    )
  }

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
          onChange={(valor) => {
            setTamanhoFonte(valor)
            levarParaConta({ tamanhoFonte: valor })
          }}
        />
      </Opcao>
      <Opcao titulo="Fundo de alto contraste" descricao="Cores mais fortes para leitura.">
        <Segmentado
          rotulo="Fundo de alto contraste"
          opcoes={[...simNao]}
          valor={altoContraste ? 'sim' : 'nao'}
          onChange={(valor) => {
            setAltoContraste(valor === 'sim')
            levarParaConta({ altoContraste: valor === 'sim' })
          }}
        />
      </Opcao>
      <Opcao titulo="Reduzir animações" descricao="Desliga movimentos e transições.">
        <Segmentado
          rotulo="Reduzir animações"
          opcoes={[...simNao]}
          valor={reduzirAnimacoes ? 'sim' : 'nao'}
          onChange={(valor) => {
            setReduzirAnimacoes(valor === 'sim')
            levarParaConta({ reduzirAnimacoes: valor === 'sim' })
          }}
        />
      </Opcao>
    </>
  )
}
