import { useEffect, useRef } from 'react'
import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import { obterAccessToken, renovarAutenticacao } from '@/services/api'
import {
  ClienteTempoReal,
  type EstadoConexao,
  type Evento,
  type MensagemDoCliente,
} from '@/services/tempoReal'
import { useAuthStore } from '@/stores/useAuthStore'

interface TempoRealState {
  estado: EstadoConexao
  /** O último erro que o servidor mandou, como `canal_negado`. */
  ultimoErro: { code: string; message: string } | null
}

/** O estado da conexão de tempo real, para a interface mostrar "reconectando". */
export const useTempoRealStore = create<TempoRealState>()(
  devtools(() => ({ estado: 'desligado' as EstadoConexao, ultimoErro: null }), {
    name: 'tempo-real',
    enabled: import.meta.env.DEV,
  }),
)

/** A conexão da aba. Uma só, compartilhada por todos os canais. */
export const tempoReal = new ClienteTempoReal({
  token: obterAccessToken,
  renovar: renovarAutenticacao,
  aoMudarEstado: (estado) => useTempoRealStore.setState({ estado }),
  aoErro: (ultimoErro) => useTempoRealStore.setState({ ultimoErro }),
})

/**
 * Liga a conexão enquanto há um aluno logado e desliga no logout. O `App`
 * chama ao montar, depois do `ligarSessao`; devolve a limpeza.
 *
 * O login de teste não tem token: a conexão nem tenta abrir.
 */
export function ligarTempoReal(cliente: ClienteTempoReal = tempoReal) {
  const acompanhar = (logado: boolean) => (logado ? cliente.ligar() : cliente.desligar())
  acompanhar(useAuthStore.getState().usuario !== null)
  const parar = useAuthStore.subscribe((estado, anterior) => {
    if ((estado.usuario === null) !== (anterior.usuario === null)) {
      acompanhar(estado.usuario !== null)
    }
  })
  return () => {
    parar()
    cliente.desligar()
  }
}

/** Ouve um canal enquanto o componente estiver montado. `null` não ouve nada. */
export function useCanal(canal: string | null, aoReceber: (evento: Evento) => void) {
  // A função mais recente, sem refazer a inscrição a cada render.
  const ref = useRef(aoReceber)
  useEffect(() => {
    ref.current = aoReceber
  })
  useEffect(() => {
    if (!canal) return
    return tempoReal.assinar(canal, (evento) => ref.current(evento))
  }, [canal])
}

/** Manda uma mensagem pela conexão; com ela fechada, sai quando voltar. */
export function enviarTempoReal(mensagem: MensagemDoCliente) {
  tempoReal.enviar(mensagem)
}
