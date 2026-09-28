import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-full px-3 py-0.5 text-xs font-bold transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground',
        secondary: 'bg-secondary text-secondary-foreground',
        outline: 'border border-border text-foreground',
        success: 'bg-success text-success-foreground',
        /** Tag de categoria do card de trilha ("Linguagens", "Gerais"). */
        categoria: 'bg-accent text-accent-foreground',
      },
    },
    defaultVariants: { variant: 'default' },
  },
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {
  /** De 1 a 8: pinta a badge com a cor daquele período letivo (tela 25). */
  periodo?: 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8
}

const coresPeriodo: Record<number, string> = {
  1: 'bg-periodo-1 text-foreground',
  2: 'bg-periodo-2 text-foreground',
  3: 'bg-periodo-3 text-foreground',
  4: 'bg-periodo-4 text-foreground',
  5: 'bg-periodo-5 text-foreground',
  6: 'bg-periodo-6 text-foreground',
  7: 'bg-periodo-7 text-foreground',
  8: 'bg-periodo-8 text-foreground',
}

function Badge({ className, variant, periodo, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        badgeVariants({ variant }),
        periodo ? coresPeriodo[periodo] : undefined,
        className,
      )}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
