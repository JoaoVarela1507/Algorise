import tailwindcssAnimate from 'tailwindcss-animate'

/**
 * Todas as cores vêm dos tokens definidos em `src/styles/index.css`. Não
 * adicione hex aqui: o tema de alto contraste redefine os tokens, e uma cor
 * fixa passaria batido por ele.
 *
 * @type {import('tailwindcss').Config}
 */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    container: {
      center: true,
      padding: '1rem',
      screens: { '2xl': '1280px' },
    },
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        success: {
          DEFAULT: 'hsl(var(--success))',
          foreground: 'hsl(var(--success-foreground))',
        },
        // Estados da trilha e da gamificação
        locked: 'hsl(var(--locked))',
        streak: 'hsl(var(--streak))',
        xp: 'hsl(var(--xp))',
        // Períodos letivos, usados pelo filtro da tela 25
        periodo: {
          1: 'hsl(var(--periodo-1))',
          2: 'hsl(var(--periodo-2))',
          3: 'hsl(var(--periodo-3))',
          4: 'hsl(var(--periodo-4))',
          5: 'hsl(var(--periodo-5))',
          6: 'hsl(var(--periodo-6))',
          7: 'hsl(var(--periodo-7))',
          8: 'hsl(var(--periodo-8))',
        },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 4px)',
        sm: 'calc(var(--radius) - 8px)',
      },
      fontFamily: {
        // Corpo de texto
        sans: ['Nunito', 'system-ui', 'sans-serif'],
        // Logo, títulos e números grandes — o arredondado da marca
        display: ['"Baloo 2"', 'Nunito', 'system-ui', 'sans-serif'],
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
      },
    },
  },
  plugins: [tailwindcssAnimate],
}
