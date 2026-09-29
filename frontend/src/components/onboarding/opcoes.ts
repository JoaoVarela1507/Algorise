import { Blend, Compass, Rocket, Shuffle, Sprout, Zap, type LucideIcon } from 'lucide-react'
import type { NivelExperiencia, TipoTrilha } from '@/types/usuario'

export interface OpcaoPerfil<T extends string> {
  valor: T
  titulo: string
  descricao: string
  icone: LucideIcon
}

// Compartilhadas pelo onboarding (telas 7 a 13) e pelo Perfil.
export const niveis: OpcaoPerfil<NivelExperiencia>[] = [
  {
    valor: 'baixo',
    titulo: 'Baixo',
    descricao:
      'Nunca programei antes, comecei do zero. Prefiro me sentir guiado(a) até saber mais.',
    icone: Sprout,
  },
  {
    valor: 'medio',
    titulo: 'Médio',
    descricao:
      'Conheço a lógica básica mas quero evoluir. Já consigo me virar em desafios mais simples.',
    icone: Zap,
  },
  {
    valor: 'alto',
    titulo: 'Alto',
    descricao:
      'Já programo há algum tempo e sei a lógica muito bem. Busco aperfeiçoar algoritmos, estruturas de dados e projetos.',
    icone: Rocket,
  },
]

export const trilhas: OpcaoPerfil<TipoTrilha>[] = [
  {
    valor: 'guiada',
    titulo: 'Guiada',
    descricao: 'Seu plano de estudos é criado automaticamente com base na ementa da sua faculdade.',
    icone: Compass,
  },
  {
    valor: 'livre',
    titulo: 'Livre',
    descricao:
      'Você escolhe e monta o seu próprio caminho de estudos, explorando os módulos na ordem que quiser.',
    icone: Shuffle,
  },
  {
    valor: 'mista',
    titulo: 'Mista',
    descricao:
      'Você escolhe o que quer estudar, combinando a ordem da sua faculdade com a liberdade de explorar outros módulos.',
    icone: Blend,
  },
]
