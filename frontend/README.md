# Algorise — Frontend

Interface web do Algorise.

## Stack

- React 18 + TypeScript
- Vite
- Tailwind CSS
- React Router

## Estrutura de pastas

```
src/
  assets/        imagens, ícones, mascote
  components/
    common/      botões, cards, inputs reutilizáveis
    layout/      Sidebar, cabeçalhos
    gamification/ XP, ranking, streak, progresso
    exercises/   componentes dos tipos de exercício (múltipla escolha, ordenação, lacunas)
  layouts/       AppLayout (área logada) e AuthLayout (onboarding/login/cadastro)
  pages/         uma pasta por tela do fluxo
  routes/        configuração de rotas
  contexts/      AuthContext, AccessibilityContext
  hooks/         hooks customizados
  services/      chamadas de API para o backend
  types/         tipos compartilhados (usuário, trilha, questão)
  styles/        estilos globais e tokens de tema
  utils/         funções utilitárias
```

## Paleta de cores

| Token        | Hex       | Uso                   |
| ------------ | --------- | --------------------- |
| salmon       | `#E8846A` | Cor primária          |
| salmon-light | `#F2B5A0` | Destaques secundários |
| beige        | `#FAF0E6` | Fundo                 |
| success      | `#4CAF50` | Acerto                |
| error        | `#E53935` | Erro                  |

Fonte: **Baloo 2** (Google Fonts).

## Rodando o projeto

```bash
npm install
cp .env.example .env
npm run dev
```

Sobe em `http://localhost:5173`. Espera o backend rodando em `http://localhost:8000` (configurável via `VITE_API_URL`).

## Testes

```bash
npm run test          # Vitest, uma vez
npm run test:watch    # durante o desenvolvimento
npm run test:cov      # com cobertura
npm run test:e2e      # Playwright, ponta a ponta
```

O Vitest roda em `jsdom`, sem rede e sem backend no ar: o `fetch` é dublado nos
testes da camada de API, e as telas montam com Testing Library. O que o jsdom
não implementa (`matchMedia`, `ResizeObserver`) está em `src/setupTests.ts`.

A cobertura tem **limiar por arquivo**, não global (ver `vite.config.ts`): a
maior parte das telas chegou antes da suíte, então um número global só poderia
ser baixo demais para significar algo. Tela nova entra na lista junto com o
teste dela.

### E2E

O Playwright sobe backend e frontend sozinho. Antes da primeira vez:

```bash
npx playwright install chromium
docker compose up -d redis     # a sessão vive no Redis
```

O banco do E2E é um SQLite descartável, montado a partir dos modelos
(`backend/scripts/preparar_e2e.py`). Depois de uma falha,
`npx playwright show-report` abre o rastro do que aconteceu.

## Autenticação

O login, o cadastro, a recuperação de senha e o login social falam com a API
(`src/services/auth.ts`); o `AuthContext` guarda quem está logado.

- **access token** só em memória (vale 15 minutos). Num 401, `apiFetch` renova a
  sessão e repete a chamada — as rotas privadas só precisam usar `apiGet`/`apiPost`.
- **refresh token** no `localStorage` com "manter-se conectado" e no
  `sessionStorage` sem. Ao recarregar a página, é ele que traz a sessão de volta.
- A renovação é compartilhada entre chamadas simultâneas: o backend gasta o
  refresh a cada uso, e duas renovações em paralelo derrubariam o aluno.
- `/auth/callback` recebe a volta do GitHub/Google e `/redefinir-senha` é o
  destino do link de "Esqueceu a senha?" (que, por enquanto, vai para o log do
  backend).

**Login de teste:** `teste@email.com` / `12345678` entra sem passar pela API,
para navegar pelo app sem backend. Ele não tem token, então telas que chamam rota
privada recebem 401 com esse usuário. Desliga com `VITE_LOGIN_TESTE=false`.
