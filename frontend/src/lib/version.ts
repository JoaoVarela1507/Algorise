export const appVersion = {
  versao: __APP_VERSION__,
  commit: __APP_COMMIT__,
  build: __APP_BUILD__,
} as const

/** Rótulo curto exibido na interface, ex.: "v0.1.0 · ef4ac6f". */
export const versaoCurta = `v${appVersion.versao} · ${appVersion.commit}`
