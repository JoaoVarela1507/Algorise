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

## [0.4.0](https://github.com/JoaoVarela1507/Algorise/compare/v0.3.0...v0.4.0) (2026-09-21)


### Adicionado

* persistir trilhas em PostgreSQL com SQLAlchemy e Alembic ([#73](https://github.com/JoaoVarela1507/Algorise/issues/73)) ([b17509e](https://github.com/JoaoVarela1507/Algorise/commit/b17509edfa54ae50ba17612b11e6a4fbbc7f25fa))

## [0.3.0](https://github.com/JoaoVarela1507/Algorise/compare/v0.2.0...v0.3.0) (2026-09-21)


### Adicionado

* adicionar shadcn/ui e design tokens do protótipo ([#58](https://github.com/JoaoVarela1507/Algorise/issues/58)) ([58fc8dc](https://github.com/JoaoVarela1507/Algorise/commit/58fc8dcc458aef238233cd50894e222a66c92f2e))
* conectar o backend ao PostgreSQL com sessão por request ([#63](https://github.com/JoaoVarela1507/Algorise/issues/63)) ([eb78870](https://github.com/JoaoVarela1507/Algorise/commit/eb788703c59c02b0646481ec21da0e3185cc8be6))

## [0.2.0](https://github.com/JoaoVarela1507/Algorise/compare/v0.1.0...v0.2.0) (2026-09-20)


### Adicionado

* containerizar o stack e adicionar CI e Dependabot ([b67728b](https://github.com/JoaoVarela1507/Algorise/commit/b67728b69440b3ade2fd26082574bfb71c1b827e))
* containerizar o stack e adicionar CI e Dependabot ([638e305](https://github.com/JoaoVarela1507/Algorise/commit/638e3056ac126dbe3a6173fbddc1b060a80332a6))
* expor versão de front e back via endpoint ([aeeadd9](https://github.com/JoaoVarela1507/Algorise/commit/aeeadd946be87957b6c675228ed813db4723b762))
* expor versão de front e back via endpoint ([885bd8d](https://github.com/JoaoVarela1507/Algorise/commit/885bd8d430faba6fd7262074f7a05e0ec7e5e050)), closes [#42](https://github.com/JoaoVarela1507/Algorise/issues/42)
* versionar automaticamente com release-please ([4e45f78](https://github.com/JoaoVarela1507/Algorise/commit/4e45f7889e62c0548a79fcf9a8ea165bd9bc1886)), closes [#42](https://github.com/JoaoVarela1507/Algorise/issues/42)


### Corrigido

* trocar TestClient por uvicorn no smoke do CI ([91ef54e](https://github.com/JoaoVarela1507/Algorise/commit/91ef54eb4ee76b346b40a39f761cbb0a1fb92fd8))

## 0.1.0 (2026-09-19)

### Adicionado

- Estrutura inicial do monorepo: frontend em React + Vite + TypeScript + Tailwind
  e backend em FastAPI.
