/**
 * Roda antes de cada arquivo de teste (ver `test.setupFiles` no vite.config).
 *
 * O que está aqui é o que o jsdom não implementa e os componentes usam: sem
 * isso, cada teste de componente quebraria por motivo alheio ao que ele testa.
 */
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

// O Testing Library desmonta sozinho no modo global, mas só quando `globals`
// está ligado *e* o ambiente é detectado; deixar explícito evita um teste
// enxergar a tela do anterior.
afterEach(() => {
  cleanup()
  localStorage.clear()
  sessionStorage.clear()
})

// `matchMedia` é usado pelo tema e pelas preferências de acessibilidade.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }),
})

// O Radix UI (usado pelo select, pelo checkbox e pelo dialog) precisa dos três
// no jsdom: sem eles, montar qualquer tela com um desses componentes quebra por
// motivo alheio ao que o teste queria verificar.
window.HTMLElement.prototype.scrollIntoView = vi.fn()
window.HTMLElement.prototype.hasPointerCapture = vi.fn()

class ResizeObserverFalso {
  observe = vi.fn()
  unobserve = vi.fn()
  disconnect = vi.fn()
}

window.ResizeObserver = ResizeObserverFalso as unknown as typeof ResizeObserver
