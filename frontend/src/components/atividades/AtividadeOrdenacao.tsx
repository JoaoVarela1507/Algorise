import { ArrowDown, ArrowUp } from 'lucide-react'
import { useState } from 'react'
import { motion } from 'framer-motion'
import { MolduraAtividade } from '@/components/atividades/MolduraAtividade'
import type { PropsDaAtividade } from '@/components/atividades/tipos'
import { Button } from '@/components/ui/button'
import { useCorrecao } from '@/hooks/useAtividades'

/**
 * Ordenação (tela 30): sobe e desce as linhas até o programa ficar na ordem.
 *
 * Botões em vez de arrastar: funcionam igual no celular, no teclado e no
 * leitor de tela, sem biblioteca de drag-and-drop.
 */
export function AtividadeOrdenacao({ atividade, numero, total, aoAvancar }: PropsDaAtividade) {
  const correcao = useCorrecao(atividade.id, atividade.concluida)
  const [linhas, setLinhas] = useState(atividade.opcoes ?? [])
  const travada = correcao.estado === 'certa'

  function mover(de: number, para: number) {
    setLinhas((atuais) => {
      const novas = [...atuais]
      const [linha] = novas.splice(de, 1)
      novas.splice(para, 0, linha)
      return novas
    })
  }

  return (
    <MolduraAtividade
      numero={numero}
      total={total}
      enunciado={atividade.enunciado}
      dica={atividade.dica}
      tempoSugeridoSegundos={atividade.tempo_sugerido_segundos}
      correcao={correcao}
      instrucao="Use as setas para pôr as linhas na ordem e confira."
      porQueBloqueado="O botão Avançar libera depois que você acertar a ordem."
      aoAvancar={aoAvancar}
    >
      <ol className="flex flex-col gap-2" aria-label="Linhas do programa">
        {linhas.map((linha, i) => (
          <motion.li
            key={linha}
            layout
            transition={{ type: 'spring', stiffness: 500, damping: 35 }}
            className="flex items-center gap-2 rounded-lg border-2 border-border bg-[#11161d] p-2"
          >
            <span className="w-6 shrink-0 text-center font-mono text-xs text-[#8b949e]" aria-hidden>
              {i + 1}
            </span>
            <pre className="min-w-0 flex-1 overflow-x-auto font-mono text-sm text-[#e6edf3]">
              <code>{linha}</code>
            </pre>
            {!travada && (
              <span className="flex shrink-0 gap-1">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="size-8 text-[#e6edf3] hover:bg-white/10 hover:text-white"
                  disabled={i === 0}
                  onClick={() => mover(i, i - 1)}
                  aria-label={`Subir a linha ${i + 1}`}
                >
                  <ArrowUp className="size-4" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="size-8 text-[#e6edf3] hover:bg-white/10 hover:text-white"
                  disabled={i === linhas.length - 1}
                  onClick={() => mover(i, i + 1)}
                  aria-label={`Descer a linha ${i + 1}`}
                >
                  <ArrowDown className="size-4" />
                </Button>
              </span>
            )}
          </motion.li>
        ))}
      </ol>

      {!travada && (
        <Button
          variant="secondary"
          className="self-start"
          disabled={correcao.enviando}
          onClick={() => void correcao.enviar(JSON.stringify(linhas))}
        >
          Conferir
        </Button>
      )}
    </MolduraAtividade>
  )
}
