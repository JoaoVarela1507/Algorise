import { useEffect } from 'react'
import { useAccessibility } from '@/contexts/AccessibilityContext'
import { useAuth } from '@/contexts/AuthContext'

/**
 * Ao entrar, aplica a acessibilidade guardada na conta.
 *
 * Só na troca de aluno (login, sessão restaurada), e não a cada atualização do
 * perfil: depois disso quem manda é o que o aluno muda na tela, e
 * `OpcoesAcessibilidade` leva a mudança para a conta. O navegador continua
 * guardando a sua cópia, porque a tela de login abre antes de saber quem é o
 * aluno.
 */
export function PreferenciasDaConta() {
  const { usuario } = useAuth()
  const { setTamanhoFonte, setAltoContraste, setReduzirAnimacoes } = useAccessibility()
  const preferencias = usuario?.preferencias

  useEffect(() => {
    if (!preferencias) return
    setTamanhoFonte(preferencias.tamanhoFonte)
    setAltoContraste(preferencias.altoContraste)
    setReduzirAnimacoes(preferencias.reduzirAnimacoes)
    // Só quando muda o aluno; ver o comentário acima.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [usuario?.id])

  return null
}
