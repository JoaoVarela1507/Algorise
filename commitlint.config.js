/**
 * O título do PR (que vira a mensagem do squash) é o que o release-please lê
 * para decidir a versão. Este hook garante o mesmo formato já nos commits
 * locais — ver a seção "Contribuindo" do README.
 */
export default {
  extends: ['@commitlint/config-conventional'],
  rules: {
    // Descrições em português costumam passar de 72 caracteres.
    'header-max-length': [2, 'always', 100],
    // 'subject-case' padrão reclama de acentuação e siglas (API, XP, JWT).
    'subject-case': [0],
  },
}
