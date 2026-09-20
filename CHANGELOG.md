# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e versionamento [SemVer](https://semver.org/lang/pt-BR/).

Frontend e backend têm versões próprias (`frontend/package.json` e
`backend/app/__init__.py`), mas são liberados juntos a cada tag `vX.Y.Z`.

## [Não lançado]

### Adicionado

- Endpoint `GET /version` na API, com versão, commit, data de build e ambiente.
- `version.json` publicado no build do frontend, com os mesmos dados.
- Versão e commit exibidos no rodapé da navegação lateral.

## [0.1.0] - 2026-09-19

### Adicionado

- Estrutura inicial do monorepo: frontend em React + Vite + TypeScript + Tailwind
  e backend em FastAPI.
