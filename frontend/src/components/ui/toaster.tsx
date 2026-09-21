import { Toaster as Sonner, toast } from 'sonner'

/**
 * Toasts do app. As cores saem dos tokens, então o alto contraste também vale
 * aqui.
 */
function Toaster(props: React.ComponentProps<typeof Sonner>) {
  return (
    <Sonner
      className="font-sans"
      toastOptions={{
        classNames: {
          toast: 'rounded-lg border border-border bg-card text-card-foreground',
          description: 'text-muted-foreground',
          actionButton: 'bg-primary text-primary-foreground',
        },
      }}
      {...props}
    />
  )
}

export { Toaster, toast }
