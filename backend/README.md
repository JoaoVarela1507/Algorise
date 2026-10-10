# Algorise API

Backend em FastAPI do Algorise.

## Rodando o projeto

Primeira vez (instala as dependências):

```powershell
pip install -r requirements.txt
copy .env.example .env
```

Nas próximas vezes, só:

```powershell
cd backend
python main.py
```

A API sobe em `http://localhost:8000`. Documentação automática em `http://localhost:8000/docs`.

O backend precisa de um PostgreSQL e usa um Redis. O jeito mais simples é subir
os dois pelo compose, da raiz do repositório:

```powershell
docker compose up -d db redis
```

### Banco no Supabase

Em vez do PostgreSQL do Docker, dá para apontar para o projeto no Supabase. No
`.env`, `DATABASE_URL` usa o **Session pooler** (em _Connect_ no painel):

```
DATABASE_URL=postgresql+psycopg://postgres.<id-do-projeto>:<senha>@aws-0-sa-east-1.pooler.supabase.com:5432/postgres?sslmode=require
```

- não use o host direto `db.<id>.supabase.co`: ele só tem IPv6, e a maioria das
  redes domésticas não alcança;
- nem o Transaction pooler (porta 6543): ele não suporta os prepared statements
  do psycopg;
- senha com caractere especial vai URL-encoded (`@` vira `%40`).

Depois, `alembic upgrade head` e `python -m app.seeds` criam o schema e o
conteúdo lá. O Redis continua local (`docker compose up -d redis`).

**Todas as tabelas têm RLS ligado e nenhuma policy.** O Supabase expõe o schema
`public` pela Data API a quem tiver a chave `anon`, que é pública; sem RLS a
tabela `usuarios` ficaria legível por ela. O backend conecta como dono das
tabelas e não é afetado. Tabela nova precisa ligar o RLS na própria migração.

## Migrações (Alembic)

O schema é versionado: nunca crie tabela na mão nem use `create_all` fora de
teste.

```powershell
alembic upgrade head           # aplica tudo que está pendente
alembic downgrade -1           # desfaz a última
alembic current                # em que revisão o banco está
```

Depois de mudar um modelo em `app/models/`, gere a migração:

```powershell
alembic revision --autogenerate -m "descricao curta"
```

**Sempre leia o arquivo gerado antes de commitar.** O autogenerate erra em dois
casos que já apareceram aqui:

- não remove tipos `ENUM` no `downgrade` — é preciso acrescentar o `DROP TYPE`
- não detecta renomeação: ele gera um `drop` mais um `add`, que apaga os dados

Teste a ida e a volta antes de abrir o PR — o CI roda `upgrade`, `downgrade` e
`upgrade` de novo, e reprova se o downgrade estiver quebrado.

## Redis

Cache e dados voláteis. O que está lá:

| Chave                              | Estrutura  | Para quê                                  |
| ---------------------------------- | ---------- | ----------------------------------------- |
| `algorise:ranking:xp`              | sorted set | ranking geral: pódio, lista e posição     |
| `algorise:ranking:trilha:<id>`     | sorted set | ranking de uma trilha (telas 16 e 17)     |
| `algorise:trilhas:catalogo:*`      | string     | catálogo por busca e período (telas 24/25) |
| `algorise:streak:visto:<id>:<dia>` | string     | acesso do dia já contabilizado            |
| `algorise:sessao:refresh:<jti>`    | string     | refresh token válido e seu dono            |
| `algorise:sessao:revogada:<jti>`   | string     | sessão revogada até o fim do prazo        |
| `algorise:ratelimit:<chave>`       | contador   | janela do rate limit                      |
| `algorise:login:falhas:<hash>`     | contador   | tentativas de login erradas por e-mail    |

**A API funciona sem ele.** Todo acesso passa por `executar()`, em
`app/core/redis.py`, que engole erro de conexão e devolve um padrão — a rota então
segue pelo PostgreSQL. Dá para conferir derrubando o Redis:

```powershell
docker compose stop redis
```

O `/ready` passa a mostrar `"redis": "erro"`, e continua devolvendo 200: sem cache
a API está mais lenta, não fora do ar.

Uma exceção declarada: em `app/services/sessoes.py` o Redis é a fonte da verdade,
não cache. Lá a falha é **fechada** (o refresh não é aceito e o aluno refaz o
login), porque aceitar um token que não se consegue verificar viraria brecha de
autenticação. No rate limit é o contrário, falha **aberta**: liberar a requisição
é melhor do que derrubar o chat.

Quem concede XP deve chamar `app/services/xp.py`, não escrever em `xp_eventos` na
mão — é ele que corrige o ranking em seguida.

## Autenticação

JWT para a sessão e OAuth2 para os botões de GitHub e Google da tela 5.

| Rota                         | O que faz                                          |
| ---------------------------- | -------------------------------------------------- |
| `POST /auth/register`        | cria a conta e já devolve a sessão                 |
| `POST /auth/login`           | e-mail e senha; `lembrar` alonga o refresh          |
| `POST /auth/refresh`         | troca o par de tokens e revoga o anterior          |
| `POST /auth/logout`          | revoga a sessão                                     |
| `GET /auth/eu`               | rota protegida de referência                        |
| `POST /auth/esqueci-senha`   | gera o link de recuperação (hoje vai para o log)   |
| `POST /auth/redefinir-senha` | troca a senha e derruba as sessões abertas         |
| `GET /auth/{provedor}/login` | começa o fluxo do GitHub ou do Google               |

Para proteger uma rota, peça o aluno pela dependência:

```python
from app.api.deps import UsuarioAtual


@router.get("/minhas-trilhas")
def minhas_trilhas(usuario: UsuarioAtual) -> list[Trilha]:
    return servico.trilhas_do_aluno(usuario.id)
```

**Dois tokens, dois prazos.** O access vale 15 minutos e é verificado só pela
assinatura — nenhuma consulta ao Redis, senão o Redis fora derrubaria toda a API
autenticada. O refresh vale uma semana (um mês com "manter-se conectado"), vive
no Redis e é rotacionado: renovar gasta o anterior (`GETDEL`, então dois refresh
simultâneos com o mesmo token não rendem dois pares) e mantém o "manter-se
conectado" do login. Um refresh vazado para de servir assim que o dono usar o dele. O preço do access não ser consultado é
que o logout leva até 15 minutos para valer; o refresh morre na hora.

### Segredos

`JWT_SECRET` e as credenciais do GitHub e do Google vêm do ambiente, e o
`.env.example` traz as chaves em branco — **não commite secret nenhum**. Em
desenvolvimento, em branco cai num segredo fixo conhecido; em produção a API se
recusa a subir assim, ou com um segredo de menos de 32 caracteres.

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Sem as credenciais do provedor, `/auth/github/login` responde 503 com a razão em
vez de mandar o aluno para uma tela de erro do GitHub. Os callbacks a cadastrar
no provedor são `http://localhost:8000/api/v1/auth/github/callback` e o equivalente do
Google.

### Hash de senha

Com `bcrypt` direto, e não com `passlib`, que a issue original pedia: o passlib
1.7.4 é de 2020, não funciona com o bcrypt 5 e, mesmo com o bcrypt 4, imprime um
traceback a cada boot ao tentar ler a versão. O limite de 72 bytes do algoritmo é
recusado na validação em vez de truncado em silêncio.

## Segurança e LGPD

O que vale para toda a API (#40):

- **Headers de segurança** em toda resposta (`app/core/protecao_http.py`):
  `nosniff`, `X-Frame-Options`, `Referrer-Policy` e uma CSP que não deixa nada
  executar. O `/docs` fica sem a CSP, porque o Swagger carrega script de CDN. O
  HSTS só é enviado em produção.
- **Teto de 10 MB** no corpo de qualquer requisição: acima disso, 413, antes de a
  rota ler o corpo. Cada rota de upload (ementa, avatar) ainda aplica o seu
  limite e confere o tipo do arquivo.
- **CORS** só para `FRONTEND_ORIGIN` e só com os métodos e headers que o
  frontend usa. Em produção a API não sobe com `*`.
- **Rate limit por IP** nas rotas de `/auth` (20 por minuto por rota), e por aluno
  no chat. Atrás de proxy, o uvicorn precisa de `--proxy-headers` e do IP do proxy
  em `--forwarded-allow-ips`, senão todo mundo divide o limite do IP do proxy.
- **Bloqueio de login:** 5 senhas erradas seguidas no mesmo e-mail bloqueiam
  aquele e-mail por 15 minutos, com ou sem conta por trás (senão o bloqueio
  entregaria quem tem conta). Redefinir a senha libera.
- **Política de senha** no cadastro e na redefinição (`app/core/politica_senha.py`),
  no estilo do NIST: mínimo de 8, sem senha comum, sequência ou senha com o e-mail
  ou o username. Sem regra de composição, de propósito.

Direitos do titular:

| Rota                     | O que faz                                                      |
| ------------------------ | -------------------------------------------------------------- |
| `GET /usuarios/me/dados` | baixa, em JSON, tudo o que o Algorise guarda sobre o aluno     |
| `DELETE /usuarios/me`    | desativa a conta agora e marca o expurgo para daqui a 30 dias |

O cadastro exige `aceite_termos: true` e grava o aceite em `consentimentos`
(versão dos termos, data e IP). A conta criada pelo GitHub ou pelo Google grava o
mesmo registro, com origem `oauth`. Mudar `VERSAO_TERMOS` é o que torna um aceite
antigo desatualizado.

A exclusão pede a palavra `EXCLUIR` e, se a conta tiver senha, a senha. Durante o
prazo a conta some do ranking, as sessões caem e o access token para de valer;
entrar de novo cancela a exclusão. O expurgo roda fora da API, uma vez por dia:

```powershell
python -m app.tarefas.expurgo
```

Ele é idempotente, e atrasar um dia só adia o expurgo. Não há nada para
anonimizar hoje: todas as tabelas com dado do aluno apagam em cascata. **Toda
tabela nova com `usuario_id` entra na exportação sozinha** (ela é descoberta pelo
mapeamento), mas precisa de `ondelete="CASCADE"` para sair no expurgo, e de RLS
na migração.

## Testes

```powershell
pytest                      # a suíte inteira
pytest tests/test_auth.py   # um arquivo
pytest -k refresh           # por nome
pytest --cov=app            # com cobertura
```

Roda em máquina sem Docker: o banco é SQLite na memória, recriado a cada teste,
e o Redis é o `fakeredis`. As fixtures estão em `tests/conftest.py` — `cliente`
(HTTP da aplicação), `usuario`, `autenticado`, `trilha`, `redis_falso` e
`redis_fora`, essa última para os testes de degradação.

O que fica de fora daqui, de propósito: migração é verificada pelo CI contra um
PostgreSQL de verdade (`upgrade`, `downgrade`, `upgrade`), porque a migração de
RLS é PostgreSQL puro.

A suíte roda com **aviso virando erro** (`filterwarnings = ["error"]` no
`pyproject.toml`). É como um `setex` obsoleto aparece antes de virar quebra numa
atualização de biblioteca. Se um aviso de dependência sem solução aparecer,
acrescente a exceção na lista, com o motivo.

O CI reprova abaixo de **80% de cobertura**.

## Contrato da API

Tudo que é contrato com o frontend vive sob **`/api/v1`**. Fora do prefixo ficam
`/health`, `/ready` e `/version`: são de operação, e o healthcheck do container
não pode mudar de endereço porque a API subiu para a v2.

### Nomes

Rota em português, no plural, com hífen quando tem mais de uma palavra
(`/api/v1/usuarios/me`, `/api/v1/auth/esqueci-senha`). Campo em `snake_case`,
também em português (`nome_exibicao`, `tamanho_pagina`) — a exceção são os campos
que o OAuth2 define, como `access_token` e `token_type`, que seguem o padrão.

### Erro

Toda falha sai igual, seja 404, 422 ou 500:

```json
{
  "erro": {
    "code": "trilha_nao_encontrada",
    "message": "Trilha não encontrada",
    "details": { "slug": "python" },
    "request_id": "5f3c9a…"
  }
}
```

`code` é estável e em inglês — é nele que o **código** do cliente decide o que
fazer. `message` é em português e pode mudar a qualquer momento: é o que o
**aluno** lê, e não serve para `if`. Para escolher o código à mão, levante
`ErroDeNegocio` em vez de `HTTPException` (ver `app/core/erros.py`).

### Paginação

Lista sempre devolve `Pagina[T]`, nunca uma lista nua:

```json
{ "itens": [], "pagina": 1, "tamanho_pagina": 20, "total": 37, "total_paginas": 2 }
```

Quem consome passa `pagina`, `tamanho_pagina` (máximo 100), `ordenar_por` e
`decrescente`. Cada rota declara por quais campos aceita ordenar; pedir outro
devolve 422 dizendo quais valem — o valor vira nome de coluna, então a lista não
é preciosismo.

### Trilhas e desbloqueio

| Rota | O que faz |
| --- | --- |
| `GET /api/v1/trilhas` | catálogo paginado; com token, cada card traz o progresso |
| `GET /api/v1/trilhas/recomendadas` | sugestões por período e nível, com o motivo |
| `GET /api/v1/trilhas/{slug}` | a trilha com o estado de cada passo |
| `GET /api/v1/trilhas/{slug}/passos/{ordem}` | conteúdo do passo; 403 se ainda não abriu |
| `POST /api/v1/trilhas/{slug}/iniciar` | começa a trilha (idempotente) |

**Quem decide o que está liberado é o servidor.** O cadeado da tela 26 é
decoração: `app/services/progresso.py` calcula o estado de cada passo a partir do
que está em `progresso_usuario`, e pedir um passo bloqueado direto na API
responde 403. O primeiro passo nasce aberto; o passo N abre quando o N-1 fecha.

O progresso **não entra no cache do catálogo**. A página fica num cache
compartilhado, igual para todo mundo, e o "3/10" de cada aluno é sobreposto no
request, com uma consulta só para a página inteira. Assim não existe uma cópia do
catálogo por aluno, e concluir um passo aparece na hora, sem esperar TTL nem
invalidação.

### Ranking

`GET /api/v1/ranking` devolve o ranking geral; com `?trilha=<slug>`, o daquela
trilha. Com token, a posição do próprio aluno vem junto, mesmo quando cai fora da
página pedida — e **só a dele**: não há parâmetro para espiar a de outro.

Os dois recortes somam coisas diferentes, e por isso vêm de lugares diferentes:

- **geral**: `usuarios.xp_total`, o saldo desnormalizado;
- **por trilha**: `SUM(xp_eventos.valor)` com `trilha_id`, porque saldo por
  trilha não existe em lugar nenhum — `xp_eventos` é a fonte da verdade, e somar
  ali é exato por construção.

`xp_eventos.trilha_id` é denormalização consciente: dava para derivar do
`referencia_id`, mas com um caminho diferente por origem (atividade → módulo →
trilha). A coluna deixa o ranking ser um `GROUP BY` em vez de três junções em
união. Eventos anteriores à coluna ficam nulos e não entram em ranking de trilha
nenhum.

### Atividades e submissões

| Rota | O que faz |
| --- | --- |
| `GET /api/v1/atividades/{id}` | enunciado, tipo, dica e tempo — **sem o gabarito** |
| `POST /api/v1/atividades/{id}/submissoes` | envia a resposta e recebe a correção |
| `GET /api/v1/atividades/{id}/submissoes` | as tentativas do próprio aluno |
| `POST /api/v1/trilhas/{slug}/passos/{ordem}/concluir` | fecha o passo, paga o bônus e diz qual é o próximo |

**A correção é do servidor.** `comando_esperado` e `resposta_esperada` nunca saem
da API antes da submissão — o terminal simulado do frontend encena a saída, mas
quem decide o acerto (e paga XP) é `app/services/submissoes.py`. Tem teste para o
gabarito não vazar.

**XP sai uma vez por atividade.** A checagem é a existência de uma tentativa
correta anterior; reenviar a resposta certa devolve `xp_ganho: 0`. O mesmo vale
para o bônus de fechar o passo.

**Toda tentativa é guardada**, não só a última: é o que permite retomar de onde
parou e é a base das métricas de aprendizado.

A resposta aberta fica **em análise**: sem a correção por IA (#11), dar XP por
texto que ninguém leu seria inventar acerto. Por isso ela também não trava o
fechamento do passo.

### Rastreio

Toda resposta traz `X-Request-Id` e `X-Response-Time-Ms`. O id vem de fora se o
proxy já mandou um, e é o mesmo que aparece no log e no corpo do erro: com o id
que o aluno mostrou na tela, o log sai por `grep`.

### Tipos do frontend

O frontend não escreve à mão os tipos que o backend já descreve:

```bash
npm run gen:api    # na raiz do repositório
```

Isso exporta o OpenAPI (sem subir servidor) e gera `frontend/src/types/api.d.ts`.
Os dois arquivos são commitados, para o frontend compilar sem Python instalado —
então **rode o comando quando mudar um schema ou uma rota**.

O `info.version` do arquivo exportado sai congelado. Ele muda a cada release, e o
CI compara o arquivo gerado com o commitado: sem isso, todo PR de release
reprovaria pedindo uma regeração que não mudaria contrato nenhum. O
`/openapi.json` que a API serve continua com a versão de verdade.

O `operation_id` de cada rota sai do nome da função Python e vira nome de tipo no
cliente gerado. Renomear a função muda o contrato gerado; é de propósito, para o
nome ser escolhido e não sorteado pela rota.

## Estrutura de pastas

```
main.py          ponto de entrada — roda o servidor (python main.py)
app/
  api/v1/        endpoints da API v1, um arquivo por recurso
  api/infra/     /health, /ready e /version — fora do contrato versionado
  api/deps.py    dependências compartilhadas (ex.: usuário autenticado)
  core/          configuração, conexões (PostgreSQL, Redis) e cache
  models/        modelos SQLAlchemy (um arquivo por área do domínio)
  schemas/       schemas Pydantic (contrato da API, espelham os types do frontend)
  services/      regras de negócio (ex.: geração de trilhas, integração com IA)
  tarefas/       rotinas de manutenção rodadas fora da API (ex.: expurgo)
scripts/         utilitários de linha de comando (ex.: exportar o OpenAPI)
  main.py        cria a instância do FastAPI (app) e registra as rotas
```
