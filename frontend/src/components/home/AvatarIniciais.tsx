import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { cn } from '@/lib/utils'

// Classes estáticas para o Tailwind enxergar; reaproveita a paleta dos períodos.
const cores = [
  'bg-periodo-1',
  'bg-periodo-2',
  'bg-periodo-3',
  'bg-periodo-4',
  'bg-periodo-5',
  'bg-periodo-6',
  'bg-periodo-7',
  'bg-periodo-8',
]

function iniciais(nome: string) {
  const partes = nome.trim().split(/\s+/)
  const primeira = partes[0]?.[0] ?? ''
  const ultima = partes.length > 1 ? partes[partes.length - 1][0] : ''
  return (primeira + ultima).toUpperCase()
}

function corPorNome(nome: string) {
  let hash = 0
  for (const letra of nome) hash = (hash * 31 + letra.charCodeAt(0)) >>> 0
  return cores[hash % cores.length]
}

/** Avatar sem foto: iniciais sobre uma cor estável derivada do nome. */
export function AvatarIniciais({ nome, className }: { nome: string; className?: string }) {
  return (
    <Avatar className={className}>
      <AvatarFallback className={cn('text-periodo-foreground', corPorNome(nome))}>
        {iniciais(nome)}
      </AvatarFallback>
    </Avatar>
  )
}
