import { defineConfig, devices } from '@playwright/test'

/**
 * E2E do fluxo principal, com frontend e backend de verdade.
 *
 * O `webServer` sobe os dois. O banco é SQLite, montado a partir dos modelos
 * (ver `scripts/preparar_e2e.py`): o E2E existe para pegar quebra **entre**
 * frontend e API — desencontro de rota, de campo, de formato de erro —, não
 * para testar o PostgreSQL, que o CI já exercita nas migrações.
 *
 * O Redis, esse sim, precisa estar de pé: a sessão vive nele e falha fechado
 * por desenho (#12), então sem ele não há cadastro nem login. No CI ele já
 * existe como serviço; na sua máquina:
 *
 *     docker compose up -d redis
 *     npx playwright install chromium   # uma vez
 */
const PORTA_API = 8001
const PORTA_WEB = 4173

export default defineConfig({
  testDir: './e2e',
  // O CI é mais lento e mais sujeito a corrida; localmente, falha é falha.
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  forbidOnly: !!process.env.CI,
  reporter: process.env.CI ? 'github' : 'list',

  use: {
    baseURL: `http://127.0.0.1:${PORTA_WEB}`,
    // Só do que falhou: rastro de todo teste que passa enche o artefato do CI.
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },

  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    // O protótipo é mobile-first e a maior parte dos alunos entra pelo celular.
    { name: 'celular', use: { ...devices['Pixel 7'] }, testMatch: /responsivo\.spec\.ts/ },
  ],

  webServer: [
    {
      command:
        `python scripts/preparar_e2e.py e2e.db && ` +
        `python -m uvicorn app.main:app --port ${PORTA_API}`,
      cwd: '../backend',
      url: `http://127.0.0.1:${PORTA_API}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        ENVIRONMENT: 'development',
        DATABASE_URL: 'sqlite:///./e2e.db',
        REDIS_URL: process.env.REDIS_URL ?? 'redis://127.0.0.1:6379/1',
        FRONTEND_ORIGIN: `http://127.0.0.1:${PORTA_WEB}`,
      },
    },
    {
      // `--host` explícito: sem ele o `vite preview` escuta só em `localhost`,
      // e a espera do Playwright, que bate em 127.0.0.1, estoura o tempo.
      command: `npm run preview -- --port ${PORTA_WEB} --strictPort --host 127.0.0.1`,
      url: `http://127.0.0.1:${PORTA_WEB}`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: { VITE_API_URL: `http://127.0.0.1:${PORTA_API}` },
    },
  ],
})
