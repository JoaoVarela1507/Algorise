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

## [0.21.0](https://github.com/JoaoVarela1507/Algorise/compare/v0.20.0...v0.21.0) (2026-10-31)


### Adicionado

* ementa a partir do PPC, com recorte do ementario e disciplinas da trilha ([#215](https://github.com/JoaoVarela1507/Algorise/issues/215)) ([7b1676d](https://github.com/JoaoVarela1507/Algorise/commit/7b1676d44f9148c6b15b9bc750937563762ee36b))

## [0.20.0](https://github.com/JoaoVarela1507/Algorise/compare/v0.19.0...v0.20.0) (2026-10-28)


### Adicionado

* revisao da ementa e trilha guiada ([#213](https://github.com/JoaoVarela1507/Algorise/issues/213)) ([b88bf02](https://github.com/JoaoVarela1507/Algorise/commit/b88bf02f3eefc0512f5f92b6b8279897ae51b31f))

## [0.19.0](https://github.com/JoaoVarela1507/Algorise/compare/v0.18.0...v0.19.0) (2026-10-27)


### Adicionado

* leitura dos assuntos da ementa e lacunas do catalogo ([#211](https://github.com/JoaoVarela1507/Algorise/issues/211)) ([b2ef817](https://github.com/JoaoVarela1507/Algorise/commit/b2ef817aa23d5268ab6bb9870f2b8a58669df13c))

## [0.18.0](https://github.com/JoaoVarela1507/Algorise/compare/v0.17.0...v0.18.0) (2026-10-27)


### Adicionado

* vault das skills de IA com pgvector ([#204](https://github.com/JoaoVarela1507/Algorise/issues/204)) ([365e6af](https://github.com/JoaoVarela1507/Algorise/commit/365e6afb0bcb8ae54cab59ef380034b98cab0ff8))

## [0.17.0](https://github.com/JoaoVarela1507/Algorise/compare/v0.16.0...v0.17.0) (2026-10-27)


### Adicionado

* estado global com Zustand (auth, onboarding, acessibilidade e tema) ([#199](https://github.com/JoaoVarela1507/Algorise/issues/199)) ([0ca4514](https://github.com/JoaoVarela1507/Algorise/commit/0ca4514957433f543eb0a498c534668d4c142888))

## [0.16.0](https://github.com/JoaoVarela1507/Algorise/compare/v0.15.0...v0.16.0) (2026-10-27)


### Adicionado

* formularios com React Hook Form e Zod, com erros acessiveis ([#197](https://github.com/JoaoVarela1507/Algorise/issues/197)) ([a7b6d8a](https://github.com/JoaoVarela1507/Algorise/commit/a7b6d8a9e47fad1517fb4a7229ae7cb33edb2d30))

## [0.15.0](https://github.com/JoaoVarela1507/Algorise/compare/v0.14.0...v0.15.0) (2026-10-27)


### Adicionado

* chat com o tutor de IA via Ollama, com streaming ([#195](https://github.com/JoaoVarela1507/Algorise/issues/195)) ([23a1680](https://github.com/JoaoVarela1507/Algorise/commit/23a1680a61278a5fb3f2c85e92c9ef02ba2a3646))

## [0.14.0](https://github.com/JoaoVarela1507/Algorise/compare/v0.13.0...v0.14.0) (2026-10-27)


### Adicionado

* onboarding com catalogo academico e upload da ementa ([#189](https://github.com/JoaoVarela1507/Algorise/issues/189)) ([4cca7e2](https://github.com/JoaoVarela1507/Algorise/commit/4cca7e2961f49b3056e1269eac5a72fc75097758))

## [0.13.0](https://github.com/JoaoVarela1507/Algorise/compare/v0.12.0...v0.13.0) (2026-10-27)


### Adicionado

* perfil com preferencias, modo de trilha, avatar e perfil publico ([#183](https://github.com/JoaoVarela1507/Algorise/issues/183)) ([94aecc2](https://github.com/JoaoVarela1507/Algorise/commit/94aecc243a98716c7130209c5db56802ea5c148f))


### Corrigido

* resolver dependencia do frontend faltando no container ([#177](https://github.com/JoaoVarela1507/Algorise/issues/177)) ([6c47123](https://github.com/JoaoVarela1507/Algorise/commit/6c471231c7b4ddc905244d1e1e6cdc35128704c2))

## [0.12.0](https://github.com/JoaoVarela1507/Algorise/compare/v0.11.0...v0.12.0) (2026-10-27)


### Adicionado

* adicionar niveis, checkin de streak e teto de XP ([#165](https://github.com/JoaoVarela1507/Algorise/issues/165)) ([7f94e9e](https://github.com/JoaoVarela1507/Algorise/commit/7f94e9e880f52a9a88a8fdb60555eb358fc1ff47))
* tela da trilha com mapa de módulos e detalhe do módulo ([#176](https://github.com/JoaoVarela1507/Algorise/issues/176)) ([a85e269](https://github.com/JoaoVarela1507/Algorise/commit/a85e26931f31fb0111afc064612fa6bd7f40d64f))

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
