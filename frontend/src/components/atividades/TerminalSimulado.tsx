import { FitAddon } from '@xterm/addon-fit'
import { Terminal } from '@xterm/xterm'
import { useCallback, useEffect, useRef, useState } from 'react'
import '@xterm/xterm/css/xterm.css'
import { PROMPT, executar, type Atividade, type Linha } from '@/lib/terminal/roteiro'
import { cn } from '@/lib/utils'

/**
 * Terminal simulado das atividades práticas (telas 28 a 33).
 *
 * O Xterm desenha e captura o teclado; o que responder vem de
 * `lib/terminal/roteiro.ts`, que não sabe o que é DOM. A divisão importa: a
 * regra é testável sem montar nada, e o componente fica só com o que é mesmo
 * de tela.
 *
 * Acessibilidade: o Xterm é um `<canvas>`, invisível para leitor de tela. Por
 * isso tudo o que aparece nele é espelhado num log de texto com `aria-live`, e
 * existe um campo de texto comum como caminho alternativo para quem navega por
 * teclado e leitor.
 */

// Cores do protótipo: fundo escuro, prompt verde, erro vermelho.
const TEMA = {
  background: '#11161d',
  foreground: '#e6edf3',
  cursor: '#4ade80',
  black: '#11161d',
  red: '#f87171',
  green: '#4ade80',
  yellow: '#fbbf24',
  blue: '#60a5fa',
  white: '#e6edf3',
}

const COR = {
  comando: '\x1b[32m', // verde
  saida: '\x1b[37m', // cinza claro
  erro: '\x1b[31m', // vermelho
  sucesso: '\x1b[1;32m', // verde forte
} as const
const RESET = '\x1b[0m'

export interface TerminalSimuladoProps {
  atividade: Atividade
  /** Chamado quando o aluno acerta o comando pedido. */
  aoAcertar?: () => void
  /** Chamado a cada comando, certo ou errado — serve para contar tentativas. */
  aoExecutar?: (comando: string, acertou: boolean) => void
  className?: string
}

export function TerminalSimulado({
  atividade,
  aoAcertar,
  aoExecutar,
  className,
}: TerminalSimuladoProps) {
  const caixa = useRef<HTMLDivElement>(null)
  const terminal = useRef<Terminal | null>(null)
  const linhaAtual = useRef('')
  const historico = useRef<string[]>([])
  const posicaoHistorico = useRef(0)
  const ocupado = useRef(false)

  // O mesmo que está no terminal, em texto, para o leitor de tela.
  const [transcricao, setTranscricao] = useState<string[]>([])
  const [entradaAlternativa, setEntradaAlternativa] = useState('')

  // Em ref porque o handler do Xterm é registrado uma vez; sem isso ele
  // chamaria sempre a primeira versão das funções.
  const callbacks = useRef({ aoAcertar, aoExecutar, atividade })
  callbacks.current = { aoAcertar, aoExecutar, atividade }

  const escrever = useCallback(async (linhas: Linha[]) => {
    const term = terminal.current
    if (!term) return

    for (const linha of linhas) {
      if (linha.atraso) {
        await new Promise((resolve) => setTimeout(resolve, linha.atraso))
      }
      term.writeln(`${COR[linha.tipo]}${linha.texto}${RESET}`)
      setTranscricao((atual) => [...atual, linha.texto])
    }
  }, [])

  const rodar = useCallback(
    async (comando: string) => {
      const term = terminal.current
      if (!term || ocupado.current) return

      setTranscricao((atual) => [...atual, `${PROMPT} ${comando}`])

      if (comando.trim()) {
        historico.current = [...historico.current, comando]
        posicaoHistorico.current = historico.current.length
      }

      // `cls` é do terminal, não do roteiro: limpar a tela não é resposta a
      // nada, é a tela sendo limpa.
      if (['cls', 'clear', 'limpar'].includes(comando.trim().toLowerCase())) {
        term.clear()
        setTranscricao([])
        term.write(`\r\n${COR.comando}${PROMPT}${RESET} `)
        return
      }

      const { linhas, acertou } = executar(comando, callbacks.current.atividade)

      ocupado.current = true
      await escrever(linhas)
      ocupado.current = false

      callbacks.current.aoExecutar?.(comando, acertou)
      if (acertou) callbacks.current.aoAcertar?.()

      term.write(`\r\n${COR.comando}${PROMPT}${RESET} `)
    },
    [escrever],
  )

  useEffect(() => {
    if (!caixa.current) return

    const term = new Terminal({
      theme: TEMA,
      fontSize: 14,
      fontFamily: '"Cascadia Code", "Fira Code", Consolas, monospace',
      cursorBlink: true,
      convertEol: true,
      // O terminal é só da atividade: rolagem longa não serve para nada aqui.
      scrollback: 200,
    })
    const ajuste = new FitAddon()
    term.loadAddon(ajuste)
    term.open(caixa.current)
    ajuste.fit()

    term.writeln(`${COR.saida}Terminal do Algorise — simulação para a atividade.${RESET}`)
    term.write(`\r\n${COR.comando}${PROMPT}${RESET} `)

    term.onData((dado) => {
      if (ocupado.current) return

      switch (dado) {
        case '\r': {
          const comando = linhaAtual.current
          linhaAtual.current = ''
          term.write('\r\n')
          void rodar(comando)
          break
        }
        case '\u007f': // backspace
          if (linhaAtual.current.length > 0) {
            linhaAtual.current = linhaAtual.current.slice(0, -1)
            // Volta uma coluna, apaga o caractere e volta de novo.
            term.write('\b \b')
          }
          break
        case '\u001b[A': // seta para cima
          if (posicaoHistorico.current > 0) {
            posicaoHistorico.current -= 1
            trocarLinha(term, historico.current[posicaoHistorico.current] ?? '')
            linhaAtual.current = historico.current[posicaoHistorico.current] ?? ''
          }
          break
        case '\u001b[B': // seta para baixo
          if (posicaoHistorico.current < historico.current.length - 1) {
            posicaoHistorico.current += 1
            trocarLinha(term, historico.current[posicaoHistorico.current] ?? '')
            linhaAtual.current = historico.current[posicaoHistorico.current] ?? ''
          } else {
            posicaoHistorico.current = historico.current.length
            trocarLinha(term, '')
            linhaAtual.current = ''
          }
          break
        default:
          // Ignora o resto das sequências de escape (setas laterais, F1…).
          if (dado >= ' ' || dado === '\t') {
            linhaAtual.current += dado
            term.write(dado)
          }
      }
    })

    const redimensionar = () => ajuste.fit()
    window.addEventListener('resize', redimensionar)
    terminal.current = term

    return () => {
      window.removeEventListener('resize', redimensionar)
      term.dispose()
      terminal.current = null
    }
  }, [rodar])

  function enviarAlternativa(evento: React.FormEvent) {
    evento.preventDefault()
    const comando = entradaAlternativa
    setEntradaAlternativa('')
    terminal.current?.write(comando)
    linhaAtual.current = ''
    terminal.current?.write('\r\n')
    void rodar(comando)
  }

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      <div
        ref={caixa}
        // `aria-hidden`: o canvas do Xterm não diz nada a leitor de tela, e o
        // conteúdo está logo abaixo, em texto.
        aria-hidden
        className="h-80 overflow-hidden rounded-lg border border-border bg-[#11161d] p-3 shadow-inner"
      />

      <form onSubmit={enviarAlternativa} className="flex gap-2">
        <label htmlFor="comando-alternativo" className="sr-only">
          Digite o comando da atividade
        </label>
        <input
          id="comando-alternativo"
          value={entradaAlternativa}
          onChange={(evento) => setEntradaAlternativa(evento.target.value)}
          placeholder="Digite o comando e pressione Enter"
          autoComplete="off"
          spellCheck={false}
          className="flex-1 rounded-lg border border-border bg-card px-3 py-2 font-mono text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
      </form>

      {/* O que saiu no terminal, em texto. `polite` para anunciar sem
          interromper o que o aluno estiver ouvindo. */}
      <div role="log" aria-live="polite" aria-label="Saída do terminal" className="sr-only">
        {transcricao.map((linha, indice) => (
          <p key={`${indice}-${linha}`}>{linha}</p>
        ))}
      </div>
    </div>
  )
}

/** Apaga a linha atual do terminal e escreve outra no lugar. */
function trocarLinha(term: Terminal, texto: string) {
  // `\x1b[2K` limpa a linha; `\r` volta para a coluna 0.
  term.write(`\x1b[2K\r${COR.comando}${PROMPT}${RESET} ${texto}`)
}
