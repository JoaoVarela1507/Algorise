import { describe, expect, it } from 'vitest'
import { roteiroDaAtividade } from '@/lib/terminal/mapa'

describe('roteiroDaAtividade', () => {
  it('acha o roteiro das duas atividades do primeiro passo', () => {
    expect(roteiroDaAtividade('introducao-python', 1, 1)?.comandoEsperado).toBe(
      'winget install Python.Python.3.14',
    )
    expect(roteiroDaAtividade('introducao-python', 1, 2)?.comandoEsperado).toBe('python --version')
  })

  it('devolve null para atividade sem roteiro, em vez de quebrar a tela', () => {
    // A atividade 3 do passo 1 é de resposta aberta: não tem terminal.
    expect(roteiroDaAtividade('introducao-python', 1, 3)).toBeNull()
    expect(roteiroDaAtividade('trilha-que-nao-existe', 1, 1)).toBeNull()
  })
})
