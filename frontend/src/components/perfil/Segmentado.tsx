import { useId } from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

/** Botões lado a lado com a seleção deslizando entre eles. */
export function Segmentado<T extends string>({
  rotulo,
  opcoes,
  valor,
  onChange,
  desabilitado,
}: {
  rotulo: string
  opcoes: { valor: T; rotulo: string }[]
  valor: T
  onChange: (valor: T) => void
  desabilitado?: boolean
}) {
  const id = useId()

  return (
    <div
      role="radiogroup"
      aria-label={rotulo}
      className="grid auto-cols-fr grid-flow-col gap-1 rounded-full bg-muted p-1"
    >
      {opcoes.map((opcao) => {
        const ativo = opcao.valor === valor
        return (
          <button
            key={opcao.valor}
            type="button"
            role="radio"
            aria-checked={ativo}
            disabled={desabilitado}
            onClick={() => onChange(opcao.valor)}
            className={cn(
              'relative rounded-full px-4 py-2 text-sm font-bold transition-colors disabled:opacity-60',
              ativo ? 'text-primary-foreground' : 'text-muted-foreground hover:text-foreground',
            )}
          >
            {ativo && (
              <motion.span
                layoutId={`segmentado-${id}`}
                className="absolute inset-0 rounded-full bg-primary shadow-sm"
                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
              />
            )}
            <span className="relative">{opcao.rotulo}</span>
          </button>
        )
      })}
    </div>
  )
}
