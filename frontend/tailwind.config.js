import tailwindcssAnimate from 'tailwindcss-animate'

/**
 * Tamanho de texto que acompanha o "Tamanho da fonte" da acessibilidade.
 * Mesmos valores do Tailwind, multiplicados por --font-scale; a altura de linha
 * escala junto (ou é proporcional, quando é um número puro).
 */
function textoEscalavel(tamanho, alturaLinha) {
  return [
    `calc(${tamanho}rem * var(--font-scale))`,
    {
      lineHeight:
        typeof alturaLinha === 'number'
          ? String(alturaLinha)
          : `calc(${alturaLinha}rem * var(--font-scale))`,
    },
  ]
}

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
          foreground: 'hsl(var(--periodo-foreground))',
        },
      },
      fontSize: {
        xs: textoEscalavel(0.75, '1'),
        sm: textoEscalavel(0.875, '1.25'),
        base: textoEscalavel(1, '1.5'),
        lg: textoEscalavel(1.125, '1.75'),
        xl: textoEscalavel(1.25, '1.75'),
        '2xl': textoEscalavel(1.5, '2'),
        '3xl': textoEscalavel(1.875, '2.25'),
        '4xl': textoEscalavel(2.25, '2.5'),
        '5xl': textoEscalavel(3, 1),
        '6xl': textoEscalavel(3.75, 1),
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
