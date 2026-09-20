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
