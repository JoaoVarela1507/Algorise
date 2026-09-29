import { Flame, Footprints, Medal, Moon, Network, Timer } from 'lucide-react'
import type { Conquista, MetaDiaria } from '@/types/gamificacao'
import type { PosicaoRanking, TrilhaAtual } from '@/types/ranking'

/**
 * Dados de exemplo da Home enquanto os endpoints de ranking (Redis) e de
 * trilha atual não estão ligados no front. O id `voce` marca o usuário logado.
 */
export const USUARIO_ATUAL_ID = 'voce'

export const rankingMock: PosicaoRanking[] = [
  { usuarioId: 'u1', nome: 'Mariana Lopes', xp: 2480, posicao: 1 },
  { usuarioId: 'u2', nome: 'Rafael Souza', xp: 2135, posicao: 2 },
  { usuarioId: 'u3', nome: 'Beatriz Nunes', xp: 1990, posicao: 3 },
  { usuarioId: 'u4', nome: 'Lucas Andrade', xp: 1720, posicao: 4 },
  { usuarioId: 'u5', nome: 'Camila Rocha', xp: 1515, posicao: 5 },
  { usuarioId: 'u6', nome: 'Pedro Henrique', xp: 1340, posicao: 6 },
  { usuarioId: USUARIO_ATUAL_ID, nome: 'Você', xp: 1205, posicao: 7 },
  { usuarioId: 'u8', nome: 'Ana Clara', xp: 980, posicao: 8 },
]

export const trilhaAtualMock: TrilhaAtual = {
  id: 'redes-de-computadores',
  nome: 'Redes de Computadores',
  disciplina: '3º período',
  modulosConcluidos: 0,
  totalModulos: 10,
  proximoModulo: 'Modelo OSI e TCP/IP',
}

export const metaDiariaMock: MetaDiaria = {
  xpHoje: 35,
  xpMeta: 50,
  desafiosResolvidos: 2,
  minutosEstudados: 18,
}

export const conquistasMock: Conquista[] = [
  {
    id: 'primeiro-passo',
    titulo: 'Primeiro passo',
    descricao: 'Resolveu o primeiro desafio.',
    icone: Footprints,
    desbloqueada: true,
  },
  {
    id: 'em-chamas',
    titulo: 'Em chamas',
    descricao: 'Estudou 3 dias seguidos.',
    icone: Flame,
    desbloqueada: true,
  },
  {
    id: 'top-10',
    titulo: 'Top 10',
    descricao: 'Entrou no top 10 do ranking da trilha.',
    icone: Medal,
    desbloqueada: true,
  },
  {
    id: 'coruja',
    titulo: 'Coruja',
    descricao: 'Resolveu um desafio depois da meia-noite.',
    icone: Moon,
    desbloqueada: false,
  },
  {
    id: 'maratonista',
    titulo: 'Maratonista',
    descricao: 'Estudou 60 minutos em um único dia.',
    icone: Timer,
    desbloqueada: false,
  },
  {
    id: 'mestre-das-redes',
    titulo: 'Mestre das redes',
    descricao: 'Concluiu a trilha de Redes de Computadores.',
    icone: Network,
    desbloqueada: false,
  },
]
