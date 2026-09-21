# Algorise

Aplicativo web gamificado para o ensino de programação a estudantes ingressantes em cursos de TI, desenvolvido a partir da metodologia Human-Centered Design (HCD).

Monorepo dividido em duas pastas independentes:

```
frontend/   React + TypeScript + Vite + Tailwind CSS  (porta 5173)
backend/    Python + FastAPI                          (porta 8000)
```

Cada pasta tem seu próprio `package.json`/`requirements.txt`, `.gitignore` e README com instruções específicas.

## Rodando com Docker (recomendado)

Sobe frontend, backend, PostgreSQL e Redis de uma vez, com hot reload nos dois
lados. Só precisa do Docker Desktop instalado:

```bash
docker compose up
```

- Frontend: http://localhost:5173
- Backend (docs automáticas): http://localhost:8000/docs
- PostgreSQL: `localhost:5432` (usuário, senha e banco: `algorise`)
- Redis: `localhost:6379`

Editar arquivos em `frontend/src` ou `backend/app` recarrega sozinho. Depois de
mudar `package.json` ou `requirements.txt`, rode `docker compose up --build`.

Para derrubar tudo: `docker compose down` (com `-v` apaga também os dados do
banco).

### Variante de produção

Frontend compilado e servido por nginx na porta 8080, backend sem reload:

```bash
docker compose -f docker-compose.yml up --build
```

O `docker-compose.override.yml` é o que adapta o stack para desenvolvimento e é
carregado automaticamente; ignorá-lo com `-f docker-compose.yml` dá o perfil de
produção.

## Rodando sem Docker

Abra dois terminais:

```bash
# Terminal 1 — backend
cd backend
pip install -r requirements.txt
cp .env.example .env
python main.py
```

```bash
# Terminal 2 — frontend
cd frontend
npm install
cp .env.example .env
npm run dev
```

- Frontend: http://localhost:5173
- Backend (docs automáticas): http://localhost:8000/docs

Veja `frontend/README.md` e `backend/README.md` para detalhes de cada parte.

## Contribuindo

A `main` é protegida: nada entra sem pull request, e o CI (`Frontend`, `Backend`
e `Imagens Docker`) precisa passar.

O merge é **sempre squash**, e a mensagem do squash é o **título do PR**. Ou
seja, o título do PR é o commit que fica na `main` — e é o texto que o
[release-please](https://github.com/googleapis/release-please) lê para decidir a
próxima versão. Capriche nele; nos commits locais, o suficiente para você se
achar.

### Título do PR

```text
tipo: descrição no imperativo
```

O tipo decide o próximo número de versão:

- `feat:` — minor (0.**4**.0), funcionalidade nova
- `fix:` — patch (0.3.**1**), correção de bug
- `feat!:` — major (**1**.0.0), muda algo de forma incompatível
- `chore:`, `docs:`, `test:` — não mudam a versão
- `refactor:`, `perf:` — não mudam a versão

Exemplos que já estão no histórico:

```text
feat: adicionar shadcn/ui e design tokens do protótipo
feat: persistir trilhas em PostgreSQL com SQLAlchemy e Alembic
fix: trocar TestClient por uvicorn no smoke do CI
```

Verbo no infinitivo, minúscula depois dos dois-pontos, sem ponto final, até
cerca de 70 caracteres. Descreva **o que muda para quem usa**, não o arquivo
alterado: `feat: exibir ranking da trilha na home` é melhor que
`feat: alterar HomePage.tsx`.

### Corpo do PR

É onde vai o detalhe e o fechamento da issue:

```text
Closes #5
```

Duas armadilhas:

- **`Closes` só fecha a issue se a base do PR for a `main`.** Em PR empilhado
  (um com base no outro), o GitHub ignora a palavra-chave.
- **Se o PR resolve só parte da issue, use `Refs #5`.** Deixe o `Closes` para
  quem entregar o restante.

### Commits locais

O squash descarta os commits da branch, então eles podem ser informais no
conteúdo — mas o formato é verificado pelo `commitlint` no `commit-msg`, para
que um commit fora do padrão não passe despercebido.

### Ferramentas de qualidade

Instale uma vez, na raiz do repositório:

```bash
npm install                                          # instala os hooks do Husky
pip install -r backend/requirements-dev.txt          # Ruff
```

A partir daí, cada commit roda automaticamente, só sobre os arquivos no stage:

- **Prettier** nos arquivos do `frontend/` e nos `.json`/`.md`/`.yml` da raiz
- **ESLint** no `frontend/`
- **Ruff** (lint e formatação) no `backend/`

Para rodar na mão:

```bash
npm run format          # Prettier em tudo
npm run lint:fe         # ESLint no frontend
npm run lint:be         # Ruff no backend
```

O mesmo é verificado no CI, então um commit com `--no-verify` ainda é barrado
no pull request. O **Qodana** roda como análise extra, sem bloquear o merge.
