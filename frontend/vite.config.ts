/// <reference types="vitest/config" />
import { execSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { fileURLToPath, URL } from 'node:url'
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'

const pkg = JSON.parse(
  readFileSync(fileURLToPath(new URL('./package.json', import.meta.url)), 'utf-8'),
) as { version: string }

const version = pkg.version
const commit = process.env.GIT_COMMIT ?? lerCommitDoGit()
const build = process.env.BUILD_TIME ?? new Date().toISOString()

function lerCommitDoGit(): string {
  // O build pode rodar fora do repositório (imagem Docker, tarball): o CI
  // preenche GIT_COMMIT nesses casos e aqui só caímos para "unknown".
  try {
    return execSync('git rev-parse --short HEAD', { stdio: ['ignore', 'pipe', 'ignore'] })
      .toString()
      .trim()
  } catch {
    return 'unknown'
  }
}

/** Publica os mesmos dados do `GET /version` da API em `/version.json`. */
function versionJson(): Plugin {
  return {
    name: 'algorise-version-json',
    apply: 'build',
    generateBundle() {
      this.emitFile({
        type: 'asset',
        fileName: 'version.json',
        source: JSON.stringify({ nome: 'Algorise Web', versao: version, commit, build }, null, 2),
      })
    },
  }
}

export default defineConfig({
  plugins: [react(), versionJson()],
  define: {
    __APP_VERSION__: JSON.stringify(version),
    __APP_COMMIT__: JSON.stringify(commit),
    __APP_BUILD__: JSON.stringify(build),
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    // `jsdom` porque os testes montam componente de verdade; `globals` para
    // `describe`/`it` sem import em cada arquivo, como no resto do ecossistema.
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/setupTests.ts',
    // O padrão do Vitest também casa com `e2e/*.spec.ts`, que é do Playwright
    // e não roda aqui: sem isto, `npm run test` tenta executá-los e falha.
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    css: false,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      // Só o que tem lógica: config, tipos gerados e ponto de entrada não
      // dizem nada sobre o que está coberto.
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/types/**',
        'src/main.tsx',
        'src/**/*.d.ts',
        'src/mocks/**',
        'src/setupTests.ts',
      ],
      // Limiar por arquivo, e não um número global. A maior parte das telas
      // ainda não tem teste (elas chegaram antes da suíte), então um limiar
      // global só poderia ser baixo o bastante para não significar nada. Por
      // arquivo, o que já está coberto não pode regredir — e cada tela nova
      // entra aqui junto com o seu teste.
      thresholds: {
        'src/services/api.ts': { lines: 90, functions: 85, branches: 90 },
        'src/pages/Auth/LoginPage.tsx': { lines: 100, functions: 100, branches: 100 },
        'src/components/trilhas/TrilhaCard.tsx': { lines: 100, branches: 100 },
      },
    },
  },
  server: {
    // No Docker com a pasta montada do Windows (ou do macOS), a mudança no
    // arquivo não chega ao container como evento, e o Vite seguia servindo o
    // código antigo. O compose de desenvolvimento liga o polling.
    watch: {
      usePolling: process.env.VITE_USE_POLLING === 'true',
      interval: 300,
    },
  },
})
