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
no Redis e é rotacionado: renovar revoga o anterior, então um refresh vazado para
de servir assim que o dono usar o dele. O preço do access não ser consultado é
que o logout leva até 15 minutos para valer; o refresh morre na hora.

### Segredos

`JWT_SECRET` e as credenciais do GitHub e do Google vêm do ambiente, e o
`.env.example` traz as chaves em branco — **não commite secret nenhum**. Em
desenvolvimento, em branco cai num segredo fixo conhecido; em produção a API se
recusa a subir assim.

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Sem as credenciais do provedor, `/auth/github/login` responde 503 com a razão em
vez de mandar o aluno para uma tela de erro do GitHub. Os callbacks a cadastrar
no provedor são `http://localhost:8000/auth/github/callback` e o equivalente do
Google.

### Hash de senha

Com `bcrypt` direto, e não com `passlib`, que a issue original pedia: o passlib
1.7.4 é de 2020, não funciona com o bcrypt 5 e, mesmo com o bcrypt 4, imprime um
traceback a cada boot ao tentar ler a versão. O limite de 72 bytes do algoritmo é
recusado na validação em vez de truncado em silêncio.

## Estrutura de pastas

```
main.py          ponto de entrada — roda o servidor (python main.py)
app/
  api/routes/    endpoints da API, um arquivo por recurso
  api/deps.py    dependências compartilhadas (ex.: usuário autenticado)
  core/          configuração, conexões (PostgreSQL, Redis) e cache
  models/        modelos SQLAlchemy (um arquivo por área do domínio)
  schemas/       schemas Pydantic (contrato da API, espelham os types do frontend)
  services/      regras de negócio (ex.: geração de trilhas, integração com IA)
  main.py        cria a instância do FastAPI (app) e registra as rotas
```
