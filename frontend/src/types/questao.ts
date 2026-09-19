export type TipoQuestao = 'multipla-escolha' | 'ordenacao' | 'preencher-lacuna'

export interface Questao {
  id: string
  tipo: TipoQuestao
  enunciado: string
  codigo?: string
  opcoes?: string[]
  respostaCorreta: string | string[]
}
