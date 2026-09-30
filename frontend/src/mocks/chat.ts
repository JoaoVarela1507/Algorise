import type { Conversa, GrupoConversas } from '@/types/chat'

const MINUTO = 60_000
const HORA = 60 * MINUTO
const DIA = 24 * HORA

export const gruposIniciais: GrupoConversas[] = [{ id: 'g-algorise', nome: 'Sobre o Algorise' }]

/** Conversas de exemplo mostradas no primeiro acesso (depois ficam no localStorage). */
export function conversasIniciais(agora = Date.now()): Conversa[] {
  return [
    {
      id: 'c-polvo',
      titulo: 'Por que o uso do Polvo?',
      atualizadaEm: agora - 30 * MINUTO,
      grupoId: 'g-algorise',
      mensagens: [
        {
          id: 'm1',
          autor: 'usuario',
          conteudo: 'Por que o mascote do Algorise é um polvo?',
          criadaEm: agora - 31 * MINUTO,
        },
        {
          id: 'm2',
          autor: 'assistente',
          conteudo:
            'Porque o polvo é um dos animais mais inteligentes do mar e consegue fazer várias coisas ao mesmo tempo com seus 8 braços, igual a quem estuda programação equilibrando várias disciplinas! 🐙',
          criadaEm: agora - 30 * MINUTO,
        },
      ],
    },
    {
      id: 'c-algoritmo',
      titulo: 'Qual algoritmo é esse?',
      atualizadaEm: agora - 5 * HORA,
      mensagens: [
        {
          id: 'm3',
          autor: 'usuario',
          conteudo:
            'Qual algoritmo é esse?\n\nfor i in range(n):\n    for j in range(n - i - 1):\n        if v[j] > v[j + 1]:\n            v[j], v[j + 1] = v[j + 1], v[j]',
          criadaEm: agora - 5 * HORA - MINUTO,
        },
        {
          id: 'm4',
          autor: 'assistente',
          conteudo:
            'É o **Bubble Sort**! A cada passada ele "borbulha" o maior elemento para o fim da lista, trocando vizinhos fora de ordem. A complexidade é O(n²).',
          criadaEm: agora - 5 * HORA,
        },
      ],
    },
    {
      id: 'c-fonte',
      titulo: 'A fonte usada na aplicação',
      atualizadaEm: agora - 2 * DIA,
      grupoId: 'g-algorise',
      mensagens: [
        {
          id: 'm5',
          autor: 'usuario',
          conteudo: 'Qual a fonte usada na aplicação?',
          criadaEm: agora - 2 * DIA - MINUTO,
        },
        {
          id: 'm6',
          autor: 'assistente',
          conteudo:
            'Os títulos usam a **Baloo 2**, arredondada como a marca, e os textos usam a **Nunito**.',
          criadaEm: agora - 2 * DIA,
        },
      ],
    },
    {
      id: 'c-print',
      titulo: 'Qual a função do print?',
      atualizadaEm: agora - 3 * DIA,
      mensagens: [
        {
          id: 'm7',
          autor: 'usuario',
          conteudo: 'Qual a função do print?',
          criadaEm: agora - 3 * DIA - MINUTO,
        },
        {
          id: 'm8',
          autor: 'assistente',
          conteudo:
            'O `print` mostra valores na saída do programa (o terminal):\n\n```python\nprint("Olá, Algorise!")\n```',
          criadaEm: agora - 3 * DIA,
        },
      ],
    },
  ]
}
