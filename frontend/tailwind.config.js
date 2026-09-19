/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        salmon: {
          DEFAULT: '#E8846A',
          light: '#F2B5A0',
        },
        beige: '#FAF0E6',
        success: '#4CAF50',
        error: '#E53935',
      },
      fontFamily: {
        sans: ['"Baloo 2"', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
