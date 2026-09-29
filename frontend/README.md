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
