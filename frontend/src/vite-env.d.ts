/// <reference types="vite/client" />

// Injetados pelo Vite em tempo de build (ver vite.config.ts).
declare const __APP_VERSION__: string
declare const __APP_COMMIT__: string
declare const __APP_BUILD__: string

interface ImportMetaEnv {
  readonly VITE_API_URL?: string
  /** `false` desliga o login de teste (`teste@email.com`). Ligado por padrão. */
  readonly VITE_LOGIN_TESTE?: string
}
