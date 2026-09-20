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
})
