import type { Usuario } from '@/types/usuario'

/**
 * Login de teste, que entra sem passar pela API.
 *
 * Serve para navegar pelo app sem backend de pé. Não gera token: as telas que
 * chamarem rota privada da API recebem 401 com esse usuário. Desliga com
 * `VITE_LOGIN_TESTE=false` no `.env` do frontend.
 */
export const LOGIN_TESTE = { email: 'teste@email.com', senha: '12345678' }

export const loginTesteHabilitado = import.meta.env.VITE_LOGIN_TESTE !== 'false'

export const USUARIO_TESTE: Usuario = {
  id: 'usuario-teste',
  nome: 'Usuário Teste',
  username: 'usuario_teste',
  email: LOGIN_TESTE.email,
  nivelExperiencia: 'medio',
  tipoTrilha: 'guiada',
  xp: 0,
  streakDias: 0,
}

export function ehLoginTeste(email: string, senha: string) {
  return (
    loginTesteHabilitado &&
    email.trim().toLowerCase() === LOGIN_TESTE.email &&
    senha === LOGIN_TESTE.senha
  )
}
