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
| `algorise:ranking:xp`              | sorted set | pódio, lista rolável e posição do aluno   |
| `algorise:trilhas:catalogo:*`      | string     | catálogo por busca e período (telas 24/25) |
| `algorise:streak:visto:<id>:<dia>` | string     | acesso do dia já contabilizado            |
| `algorise:sessao:refresh:<jti>`    | string     | refresh token válido e seu dono            |
| `algorise:sessao:revogada:<jti>`   | string     | sessão revogada até o fim do prazo        |
| `algorise:ratelimit:<chave>`       | contador   | janela do rate limit                      |

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

## Estrutura de pastas

```
main.py          ponto de entrada — roda o servidor (python main.py)
app/
  api/routes/    endpoints da API, um arquivo por recurso
  core/          configuração, conexões (PostgreSQL, Redis) e cache
  models/        modelos SQLAlchemy (um arquivo por área do domínio)
  schemas/       schemas Pydantic (contrato da API, espelham os types do frontend)
  services/      regras de negócio (ex.: geração de trilhas, integração com IA)
  main.py        cria a instância do FastAPI (app) e registra as rotas
```
