import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full font-display font-bold transition-colors disabled:pointer-events-none disabled:opacity-60 [&_svg]:size-5 [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        /** Ação principal das telas: "Continuar", "Avançar", "Começar Trilha". */
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        /** Ação secundária, como as opções de nível e de trilha. */
        secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
        outline: 'border-2 border-primary bg-transparent text-primary hover:bg-primary/10',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        link: 'text-primary underline-offset-4 hover:underline',
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        /** Trilha ou passo ainda bloqueado (cadeado). */
        locked: 'cursor-not-allowed bg-locked/30 text-locked',
      },
      size: {
        default: 'h-11 px-6 text-base',
        sm: 'h-9 px-4 text-sm',
        lg: 'h-14 px-8 text-lg',
        icon: 'size-11',
      },
      /** Botões de largura cheia, como no rodapé das atividades. */
      full: { true: 'w-full', false: '' },
    },
    defaultVariants: { variant: 'default', size: 'default', full: false },
  },
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, full, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button'
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, full, className }))}
        ref={ref}
        // O visual de bloqueado também precisa bloquear de fato.
        disabled={variant === 'locked' ? true : props.disabled}
        {...props}
      />
    )
  },
)
Button.displayName = 'Button'

export { Button, buttonVariants }
