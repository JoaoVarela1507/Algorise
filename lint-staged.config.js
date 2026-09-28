/**
 * Roda no pre-commit, apenas sobre o que está no stage.
 *
 * O ESLint é chamado pelo script do frontend (e não sobre os arquivos
 * avulsos) porque a config flat do ESLint 9 é resolvida a partir do
 * diretório de trabalho, que aqui é a raiz do monorepo.
 */
export default {
  'frontend/**/*.{ts,tsx,js,jsx,css,json,md}': ['prettier --write'],
  'frontend/**/*.{ts,tsx}': () => 'npm --prefix frontend run lint',
  'backend/**/*.py': ['ruff check --fix', 'ruff format'],
  '*.{json,md,yml,yaml}': ['prettier --write'],
}
