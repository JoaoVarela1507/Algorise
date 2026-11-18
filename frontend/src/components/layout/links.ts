import { House, Map as MapaIcone, MessageCircle, Settings, UserRound } from 'lucide-react'

/**
 * As telas principais. A sidebar (desktop) e a barra de abas do celular
 * (`NavegacaoMobile`) usam a mesma lista.
 */
export const links = [
  { to: '/', label: 'Home', end: true, icone: House },
  { to: '/trilhas', label: 'Trilhas', end: false, icone: MapaIcone },
  { to: '/chat', label: 'Chat', end: false, icone: MessageCircle },
  { to: '/perfil', label: 'Perfil', end: false, icone: UserRound },
  { to: '/configuracoes', label: 'Configurações', end: false, icone: Settings },
]
