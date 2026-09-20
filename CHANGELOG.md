# Changelog

Este arquivo é gerado pelo [release-please](https://github.com/googleapis/release-please)
a partir dos commits em `main`. Não edite à mão: escreva bons commits.

Front e back compartilham uma única versão ([SemVer](https://semver.org/lang/pt-BR/)),
liberada a cada tag `vX.Y.Z`. A versão vive em `version.txt` e é propagada para
`frontend/package.json` e `backend/app/__init__.py` pelo PR de release.

O tipo do commit define o bump:

- `fix: ...` — patch (0.1.**1**)
- `feat: ...` — minor (0.**2**.0)
- `feat!: ...` ou `BREAKING CHANGE:` no corpo — major (**1**.0.0)
- `chore:`, `docs:`, `test:` — não geram release

## 0.1.0 (2026-09-19)

### Adicionado

- Estrutura inicial do monorepo: frontend em React + Vite + TypeScript + Tailwind
  e backend em FastAPI.
