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

| Token         | Hex       | Uso                      |
|---------------|-----------|--------------------------|
| salmon        | `#E8846A` | Cor primária             |
| salmon-light  | `#F2B5A0` | Destaques secundários    |
| beige         | `#FAF0E6` | Fundo                    |
| success       | `#4CAF50` | Acerto                   |
| error         | `#E53935` | Erro                     |

Fonte: **Baloo 2** (Google Fonts).

## Rodando o projeto

```bash
npm install
cp .env.example .env
npm run dev
```

Sobe em `http://localhost:5173`. Espera o backend rodando em `http://localhost:8000` (configurável via `VITE_API_URL`).
