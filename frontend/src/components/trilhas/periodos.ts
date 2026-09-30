// Classes estáticas (o Tailwind não enxerga `bg-periodo-${n}`), uma por período.
export const coresPeriodo: Record<number, { cheio: string; suave: string; borda: string }> = {
  1: { cheio: 'bg-periodo-1', suave: 'bg-periodo-1/35', borda: 'border-periodo-1' },
  2: { cheio: 'bg-periodo-2', suave: 'bg-periodo-2/35', borda: 'border-periodo-2' },
  3: { cheio: 'bg-periodo-3', suave: 'bg-periodo-3/35', borda: 'border-periodo-3' },
  4: { cheio: 'bg-periodo-4', suave: 'bg-periodo-4/35', borda: 'border-periodo-4' },
  5: { cheio: 'bg-periodo-5', suave: 'bg-periodo-5/35', borda: 'border-periodo-5' },
  6: { cheio: 'bg-periodo-6', suave: 'bg-periodo-6/35', borda: 'border-periodo-6' },
  7: { cheio: 'bg-periodo-7', suave: 'bg-periodo-7/35', borda: 'border-periodo-7' },
  8: { cheio: 'bg-periodo-8', suave: 'bg-periodo-8/35', borda: 'border-periodo-8' },
}

export const PERIODOS = [1, 2, 3, 4, 5, 6, 7, 8] as const
