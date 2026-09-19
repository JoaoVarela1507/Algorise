# Algorise

Aplicativo web gamificado para o ensino de programação a estudantes ingressantes em cursos de TI, desenvolvido a partir da metodologia Human-Centered Design (HCD).

Monorepo dividido em duas pastas independentes:

```
frontend/   React + TypeScript + Vite + Tailwind CSS  (porta 5173)
backend/    Python + FastAPI                          (porta 8000)
```

Cada pasta tem seu próprio `package.json`/`requirements.txt`, `.gitignore` e README com instruções específicas.

## Rodando o projeto (dev)

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
