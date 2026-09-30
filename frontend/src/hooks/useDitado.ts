import { useEffect, useRef, useState } from 'react'

// Tipagem mínima da Web Speech API, que ainda não está no lib.dom do TypeScript.
interface ResultadoFala {
  resultIndex: number
  results: ArrayLike<ArrayLike<{ transcript: string }>>
}

interface ReconhecimentoFala {
  lang: string
  interimResults: boolean
  continuous: boolean
  start: () => void
  stop: () => void
  onresult: ((evento: ResultadoFala) => void) | null
  onend: (() => void) | null
  onerror: (() => void) | null
}

type ConstrutorReconhecimento = new () => ReconhecimentoFala

function obterConstrutor(): ConstrutorReconhecimento | undefined {
  if (typeof window === 'undefined') return undefined
  const janela = window as unknown as {
    SpeechRecognition?: ConstrutorReconhecimento
    webkitSpeechRecognition?: ConstrutorReconhecimento
  }
  return janela.SpeechRecognition ?? janela.webkitSpeechRecognition
}

/** Ditado por voz em pt-BR (Chrome/Edge). Onde não houver suporte, `suportado` é false. */
export function useDitado(onTexto: (texto: string) => void) {
  const [ouvindo, setOuvindo] = useState(false)
  const reconhecimento = useRef<ReconhecimentoFala | null>(null)
  const onTextoRef = useRef(onTexto)
  const suportado = !!obterConstrutor()

  useEffect(() => {
    onTextoRef.current = onTexto
  })

  useEffect(() => () => reconhecimento.current?.stop(), [])

  function alternar() {
    if (ouvindo) {
      reconhecimento.current?.stop()
      return
    }
    const Construtor = obterConstrutor()
    if (!Construtor) return

    const novo = new Construtor()
    novo.lang = 'pt-BR'
    novo.interimResults = false
    novo.continuous = false
    novo.onresult = (evento) => {
      let texto = ''
      for (let i = evento.resultIndex; i < evento.results.length; i++) {
        texto += evento.results[i][0].transcript
      }
      onTextoRef.current(texto)
    }
    novo.onend = () => setOuvindo(false)
    novo.onerror = () => setOuvindo(false)

    reconhecimento.current = novo
    novo.start()
    setOuvindo(true)
  }

  return { ouvindo, suportado, alternar }
}
