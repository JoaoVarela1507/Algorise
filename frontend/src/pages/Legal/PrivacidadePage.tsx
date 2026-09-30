import { Link } from 'react-router-dom'

// Mesma versão do backend (`VERSAO_TERMOS`): o aceite registrado no cadastro
// aponta para ela. Mudou o texto de forma relevante, muda as duas.
const VERSAO = '2026-09-29'

/**
 * Termos de uso e política de privacidade (LGPD, #40).
 *
 * Rascunho escrito a partir do que o sistema guarda de fato (ver
 * `backend/app/models`). Precisa de revisão antes de o app ir a público.
 */
export function PrivacidadePage() {
  return (
    <main className="mx-auto max-w-2xl px-6 py-12 text-foreground">
      <Link to="/boas-vindas" className="text-sm font-semibold text-primary hover:underline">
        ← Voltar
      </Link>

      <h1 className="mt-6 font-display text-3xl font-bold">
        Termos de uso e política de privacidade
      </h1>
      <p className="mt-2 text-sm text-muted-foreground">Versão {VERSAO}</p>

      <div className="mt-8 flex flex-col gap-8 leading-relaxed [&_h2]:mb-2 [&_h2]:font-display [&_h2]:text-xl [&_h2]:font-bold [&_li]:ml-5 [&_li]:list-disc">
        <section>
          <h2>O que coletamos</h2>
          <ul>
            <li>
              <strong>Conta:</strong> e-mail, nome de usuário, nome de exibição, foto de perfil e a
              senha, guardada só como hash (nunca a senha em si).
            </li>
            <li>
              <strong>Login com GitHub ou Google:</strong> o identificador da sua conta no provedor
              e o e-mail verificado que ele informar. Não recebemos sua senha de lá.
            </li>
            <li>
              <strong>Dados acadêmicos:</strong> nível de experiência, modo de trilha, instituição,
              curso, período e a ementa em PDF que você enviar.
            </li>
            <li>
              <strong>Uso do app:</strong> progresso nas trilhas, respostas das atividades, XP,
              sequência de dias e certificados.
            </li>
            <li>
              <strong>Registro do aceite:</strong> a versão destes termos, a data e o IP de quando
              você os aceitou.
            </li>
          </ul>
        </section>

        <section>
          <h2>Para que usamos</h2>
          <p>
            Para manter sua conta, montar trilhas adaptadas ao seu curso, mostrar seu progresso e o
            ranking, e proteger a conta contra acessos indevidos (por exemplo, bloqueando tentativas
            seguidas de senha errada). Não vendemos seus dados nem os usamos para publicidade.
          </p>
        </section>

        <section>
          <h2>Com quem compartilhamos</h2>
          <p>
            Com o GitHub e o Google, só quando você escolhe entrar por eles, e com o serviço que
            hospeda o banco de dados. No ranking, outros alunos veem seu nome de usuário, nome de
            exibição, foto e XP.
          </p>
        </section>

        <section>
          <h2>Por quanto tempo guardamos</h2>
          <p>
            Enquanto sua conta existir. Se você pedir a exclusão, a conta é desativada na hora e os
            dados são apagados de vez em 30 dias. Entrar de novo nesse prazo cancela a exclusão.
          </p>
        </section>

        <section>
          <h2>Seus direitos</h2>
          <p>
            Pela LGPD, você pode acessar, corrigir, exportar e excluir seus dados, e retirar o
            consentimento. Em <strong>Configurações</strong> você baixa tudo o que guardamos sobre
            você e pede a exclusão da conta.
          </p>
        </section>
      </div>
    </main>
  )
}
