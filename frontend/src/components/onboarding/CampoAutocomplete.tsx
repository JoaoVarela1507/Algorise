import { useId, useState } from 'react'
import { Check, Loader2 } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'
import type { Escolha } from '@/services/onboarding'

export interface Sugestao {
  id: number
  rotulo: string
  detalhe?: string
}

/**
 * Campo de texto com sugestões (padrão combobox do WAI-ARIA).
 *
 * Escolher uma sugestão guarda o `id`; voltar a digitar o descarta. Assim o
 * texto livre nunca trava o onboarding: quem não acha a faculdade na lista
 * continua digitando e segue, e o backend grava o que foi escrito.
 */
export function CampoAutocomplete({
  id,
  rotulo,
  placeholder,
  valor,
  onChange,
  sugestoes,
  carregando = false,
}: {
  id: string
  rotulo: string
  placeholder?: string
  valor: Escolha
  onChange: (valor: Escolha) => void
  sugestoes: Sugestao[]
  carregando?: boolean
}) {
  const idLista = useId()
  const [aberto, setAberto] = useState(false)
  const [ativa, setAtiva] = useState(-1)

  const visiveis = valor.id === null ? sugestoes : []
  const expandido = aberto && visiveis.length > 0

  function escolher(sugestao: Sugestao) {
    onChange({ texto: sugestao.rotulo, id: sugestao.id })
    setAberto(false)
    setAtiva(-1)
  }

  function aoTeclar(evento: React.KeyboardEvent<HTMLInputElement>) {
    if (!expandido) return
    if (evento.key === 'ArrowDown') {
      evento.preventDefault()
      setAtiva((atual) => (atual + 1) % visiveis.length)
    } else if (evento.key === 'ArrowUp') {
      evento.preventDefault()
      setAtiva((atual) => (atual <= 0 ? visiveis.length - 1 : atual - 1))
    } else if (evento.key === 'Enter' && ativa >= 0) {
      evento.preventDefault()
      escolher(visiveis[ativa])
    } else if (evento.key === 'Escape') {
      setAberto(false)
    }
  }

  return (
    <div className="relative flex flex-col gap-1">
      <Label htmlFor={id}>{rotulo}</Label>
      <div className="relative">
        <Input
          id={id}
          role="combobox"
          autoComplete="off"
          aria-autocomplete="list"
          aria-expanded={expandido}
          aria-controls={idLista}
          aria-activedescendant={expandido && ativa >= 0 ? `${idLista}-${ativa}` : undefined}
          placeholder={placeholder}
          value={valor.texto}
          onChange={(evento) => {
            onChange({ texto: evento.target.value, id: null })
            setAberto(true)
            setAtiva(-1)
          }}
          onFocus={() => setAberto(true)}
          // Atrasado para o clique numa sugestão chegar antes de a lista sumir.
          onBlur={() => setTimeout(() => setAberto(false), 120)}
          onKeyDown={aoTeclar}
        />
        <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2">
          {carregando ? (
            <Loader2 className="size-4 animate-spin text-muted-foreground" aria-hidden />
          ) : (
            valor.id !== null && (
              <Check className="size-4 text-primary" aria-label="Escolhida da lista" />
            )
          )}
        </span>
      </div>

      <ul
        id={idLista}
        role="listbox"
        aria-label={rotulo}
        hidden={!expandido}
        className="absolute top-full z-20 mt-1 max-h-56 w-full overflow-auto rounded-lg border border-border bg-popover p-1 shadow-lg"
      >
        {visiveis.map((sugestao, indice) => (
          <li
            key={sugestao.id}
            id={`${idLista}-${indice}`}
            role="option"
            aria-selected={indice === ativa}
            // `onMouseDown` e não `onClick`: o clique vem depois do blur do campo.
            onMouseDown={(evento) => {
              evento.preventDefault()
              escolher(sugestao)
            }}
            className={cn(
              'cursor-pointer rounded-md px-3 py-2 text-sm text-popover-foreground',
              indice === ativa ? 'bg-accent' : 'hover:bg-accent/60',
            )}
          >
            <span className="font-semibold">{sugestao.rotulo}</span>
            {sugestao.detalhe && (
              <span className="ml-2 text-xs text-muted-foreground">{sugestao.detalhe}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
