import type { ReactNode } from 'react'

const ROTULOS: Record<string, string> = {
  python: 'Python',
  py: 'Python',
  javascript: 'JavaScript',
  js: 'JavaScript',
  jsx: 'JavaScript',
  typescript: 'TypeScript',
  ts: 'TypeScript',
  tsx: 'TypeScript',
  java: 'Java',
  c: 'C',
  cpp: 'C++',
  sql: 'SQL',
  bash: 'Bash',
  sh: 'Bash',
  shell: 'Bash',
  json: 'JSON',
  html: 'HTML',
  xml: 'XML',
  css: 'CSS',
}

export function rotuloDaLinguagem(linguagem?: string) {
  if (!linguagem) return 'Código'
  return ROTULOS[linguagem.toLowerCase()] ?? linguagem
}

/** O texto puro de um trecho já realçado (os <span> do highlight viram texto). */
export function textoDe(no: ReactNode): string {
  if (typeof no === 'string' || typeof no === 'number') return String(no)
  if (Array.isArray(no)) return no.map(textoDe).join('')
  if (no && typeof no === 'object' && 'props' in no) {
    return textoDe((no.props as { children?: ReactNode }).children)
  }
  return ''
}
