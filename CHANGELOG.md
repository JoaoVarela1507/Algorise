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

## [0.11.0](https://github.com/JoaoVarela1507/Algorise/compare/v0.10.0...v0.11.0) (2026-10-09)


### Adicionado

* adicionar o terminal simulado das atividades ([#155](https://github.com/JoaoVarela1507/Algorise/issues/155)) ([a3485d4](https://github.com/JoaoVarela1507/Algorise/commit/a3485d4ffa65843e21c82639ce1c5e9e3bc2333f))
* corrigir submissoes de atividade e fechar passo com XP ([#160](https://github.com/JoaoVarela1507/Algorise/issues/160)) ([856edb3](https://github.com/JoaoVarela1507/Algorise/commit/856edb36b9fe8bfa587e4432cbdc0cb32e13eff8))

## [0.10.0](https://github.com/JoaoVarela1507/Algorise/compare/v0.9.0...v0.10.0) (2026-10-03)


### Adicionado

* ligar o frontend a API com TanStack Query ([#140](https://github.com/JoaoVarela1507/Algorise/issues/140)) ([73e5fc9](https://github.com/JoaoVarela1507/Algorise/commit/73e5fc9bb6a023d247951f43a90e12de83295bc7))

## [0.9.0](https://github.com/JoaoVarela1507/Algorise/compare/v0.8.0...v0.9.0) (2026-09-30)


### Adicionado

* servir trilhas com passos, progresso e desbloqueio sequencial ([#133](https://github.com/JoaoVarela1507/Algorise/issues/133)) ([bae2c1f](https://github.com/JoaoVarela1507/Algorise/commit/bae2c1f55c615e24d0fbf3c7d9c12d21e29057d2))

## [0.8.0](https://github.com/JoaoVarela1507/Algorise/compare/v0.7.0...v0.8.0) (2026-09-30)


### Adicionado

* fixar o contrato da API com prefixo v1, erro unico e paginacao ([#117](https://github.com/JoaoVarela1507/Algorise/issues/117)) ([72f335d](https://github.com/JoaoVarela1507/Algorise/commit/72f335d7ddf4259e430888cdb37f6bd9ded34c0d))


### Corrigido

* congelar a versao no OpenAPI exportado ([#128](https://github.com/JoaoVarela1507/Algorise/issues/128)) ([f91c812](https://github.com/JoaoVarela1507/Algorise/commit/f91c8121ba57066b4bd91bd0d3e7daf6f6117bca))
* remover ReDoS polinomial na checagem de senha ([#120](https://github.com/JoaoVarela1507/Algorise/issues/120)) ([63c5818](https://github.com/JoaoVarela1507/Algorise/commit/63c58181b7704c91a739145ac744ca509fcfe04e))

## [0.7.0](https://github.com/JoaoVarela1507/Algorise/compare/v0.6.0...v0.7.0) (2026-09-29)


### Adicionado

* adicionar autenticacao JWT e login com GitHub e Google ([#94](https://github.com/JoaoVarela1507/Algorise/issues/94)) ([b75cccc](https://github.com/JoaoVarela1507/Algorise/commit/b75cccc47e972c2e03d76a33470c6dbb32b94074))
* ligar a autenticação do frontend à API e o docker compose ao Supabase ([#108](https://github.com/JoaoVarela1507/Algorise/issues/108)) ([10c7a5a](https://github.com/JoaoVarela1507/Algorise/commit/10c7a5ae6b5e5ad0cea54f3a529225b25455dc7c))
* preparar o backend para usar o Supabase como PostgreSQL ([#107](https://github.com/JoaoVarela1507/Algorise/issues/107)) ([7a6c766](https://github.com/JoaoVarela1507/Algorise/commit/7a6c766429092bcb23aae8a1a0f580f33a6c4e6b))
* telas 1, 2 e 4 (cold start e onboarding) adaptadas para web ([#102](https://github.com/JoaoVarela1507/Algorise/issues/102)) ([06ef1c0](https://github.com/JoaoVarela1507/Algorise/commit/06ef1c0ebaac95737751957692e86ab078ad156e))
* telas 5 e 6 (login e cadastro) adaptadas para web ([#104](https://github.com/JoaoVarela1507/Algorise/issues/104)) ([8f3b95d](https://github.com/JoaoVarela1507/Algorise/commit/8f3b95d54133e737da3ddaa7732cb0c9eb97649e))
* telas de home, trilhas, chat, perfil, configurações e certificados para web ([#110](https://github.com/JoaoVarela1507/Algorise/issues/110)) ([19de001](https://github.com/JoaoVarela1507/Algorise/commit/19de001f586d27d637d0c72fe78110bbe5427306))


### Corrigido

* corrigir rotação de sessão, cadastro e falhas do Redis na autenticação ([#106](https://github.com/JoaoVarela1507/Algorise/issues/106)) ([ba137e8](https://github.com/JoaoVarela1507/Algorise/commit/ba137e848ccbdeb09f693d93cd5e6093fd58b714))

## [0.6.0](https://github.com/JoaoVarela1507/Algorise/compare/v0.5.0...v0.6.0) (2026-09-22)


### Adicionado

* adicionar Redis para cache, ranking e streak ([#85](https://github.com/JoaoVarela1507/Algorise/issues/85)) ([d50a2af](https://github.com/JoaoVarela1507/Algorise/commit/d50a2afbcfb4621af2173bea2de2647222947fce))

## [0.5.0](https://github.com/JoaoVarela1507/Algorise/compare/v0.4.0...v0.5.0) (2026-09-21)


### Adicionado

* padronizar qualidade com Prettier, Ruff, Husky e lint-staged ([#76](https://github.com/JoaoVarela1507/Algorise/issues/76)) ([5effff1](https://github.com/JoaoVarela1507/Algorise/commit/5effff12936a13f46e34ba7f6c66a22b95981faa))

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
