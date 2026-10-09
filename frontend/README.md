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

## Dados do servidor

O TanStack Query cuida do cache; a `services/api.ts` continua cuidando do token e
da renovação no 401. Um entra em cima do outro, não no lugar.

```
src/lib/query.ts         QueryClient, política de nova tentativa e as chaves de cache
src/services/*.ts        chamadas de cada recurso, com os tipos vindos do OpenAPI
src/hooks/use*.ts        os hooks que as telas usam
src/components/ui/estados.tsx   carregando, vazio e erro reaproveitáveis
```

Três coisas que valem saber antes de escrever um hook novo:

- **a chave de cache vem de `chaves`, em `lib/query.ts`.** Invalidação depende de
  a chave bater exatamente; com string solta espalhada, a tela para de atualizar
  e ninguém entende por quê;
- **erro 4xx não é tentado de novo.** Um 404 ou um 403 não melhora insistindo, e
  repetir só atrasa a tela de erro;
- **busca, filtro e paginação acontecem no servidor.** A API já faz isso;
  filtrar no cliente só funcionaria enquanto tudo coubesse numa página.

Os tipos de resposta saem de `src/types/api.d.ts`, gerado do OpenAPI com
`npm run gen:api` na raiz — mudar um schema no backend e esquecer o frontend vira
erro de compilação, não bug em produção.

## Terminal simulado

As atividades práticas (telas 28 a 33) usam um terminal falso, feito com Xterm.js:

```
src/lib/terminal/roteiro.ts        o que cada comando responde — sem DOM, testável sozinho
src/lib/terminal/mapa.ts           qual roteiro pertence a qual atividade da API
src/components/atividades/TerminalSimulado.tsx    o terminal na tela
src/components/atividades/AtividadeTerminal.tsx   enunciado, tempo, progresso e "Avançar"
```

A divisão é de propósito: **o roteiro não sabe o que é tela**, então a regra tem
teste sem montar nada, e fica claro que ali é encenação — o `winget` não instala
Python nenhum.

O roteiro mora no frontend porque a API **não manda o gabarito** antes da
submissão: `comando_esperado` na resposta entregaria o exercício a quem abrisse o
devtools. A ligação entre a atividade da API e o roteiro é por posição (trilha,
passo, atividade), em `mapa.ts`. Quando a submissão existir (#30), quem diz se
acertou passa a ser o servidor e o roteiro fica só com a encenação.

**Acessibilidade:** o Xterm desenha num `<canvas>`, que leitor de tela não lê. Por
isso tudo o que sai no terminal é espelhado num log com `aria-live`, e há um campo
de texto comum como caminho alternativo — dá para concluir a atividade inteira só
pelo teclado. Esse campo é também o que os testes de componente usam, já que o
jsdom não desenha canvas; o terminal de verdade é exercitado no E2E.

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

No Git Bash do Windows, o `PATH` do shell é POSIX e o `cmd` que o Playwright usa
para subir os servidores não o entende; se der "'python' não é reconhecido",
rode o comando a partir do PowerShell.

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
