from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app import __version__

# Vale para desenvolvimento e para os testes; em produção a aplicação se recusa
# a subir com ele (ver `_conferir_segredo`).
SEGREDO_DE_DESENVOLVIMENTO = "inseguro-so-para-desenvolvimento"

PROVEDORES_DE_IA = ("ollama", "eco")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Algorise API"
    app_version: str = __version__
    environment: str = "development"
    frontend_origin: str = "http://localhost:5173"

    # Preenchidos pelo CI no build da imagem; em dev ficam como "unknown".
    git_commit: str = "unknown"
    build_time: str | None = None

    # O default serve para rodar fora do Docker; o compose injeta o host `db`.
    database_url: str = "postgresql+psycopg://algorise:algorise@localhost:5432/algorise"

    # Segundos de espera ao abrir conexão. Mantém o /ready respondendo rápido
    # quando o banco está fora.
    database_connect_timeout: int = 3

    # Mesmo raciocínio do database_url: o default é para rodar fora do Docker.
    redis_url: str = "redis://localhost:6379/0"

    # Timeout curto de propósito: o Redis é só cache, então esperar por ele é
    # pior do que ir no banco. Com o Redis fora, cada tentativa custa isso.
    redis_timeout: int = 2

    # Segundos de validade do cache. O catálogo de trilhas muda raramente; o
    # ranking, a cada XP ganho — e nele o TTL é só a rede de segurança, porque
    # a invalidação é explícita.
    cache_ttl_trilhas: int = 300
    cache_ttl_ranking: int = 60

    # Teto de XP por janela, contra farm (#31). Generoso de propósito: o aluno
    # dedicado passa longe disso, e um script varrendo o catálogo esbarra.
    xp_maximo_por_janela: int = 500
    xp_janela_segundos: int = 60 * 60

    # Janela e teto do rate limit do chat, que custa chamada de IA por request.
    rate_limit_chat_requisicoes: int = 20
    rate_limit_chat_janela: int = 60

    # IA do chat (#11): um modelo só, servido pelo Ollama. `eco` é o provedor de
    # teste, que responde sem rede — para o E2E e para rodar sem o Ollama; em
    # produção a aplicação não sobe com ele.
    ia_provedor: str = "ollama"
    ollama_url: str = "http://localhost:11434"
    ollama_modelo: str = "llama3.2"
    # Embedding do vault das skills (#200). Multilíngue, porque o conteúdo é em
    # português; a dimensão dele (1024) está fixa na tabela `vault_trechos`.
    ollama_modelo_embedding: str = "bge-m3"
    # Distância de cosseno até o módulo mais próximo no vault abaixo da qual um
    # assunto da ementa conta como coberto (#38). Acima, vira lacuna. Ponto de
    # partida a calibrar com ementas reais: a distância de cada assunto fica
    # gravada em `ementa_assuntos.distancia`.
    ementa_distancia_maxima: float = 0.35

    # Segundos. A leitura é o intervalo máximo entre dois pedaços da resposta, e
    # não o tempo total: o primeiro pedaço demora quando o Ollama ainda está
    # carregando o modelo na memória.
    ia_timeout_conexao: float = 5
    ia_timeout_leitura: float = 120
    # O mesmo intervalo para o trabalho em segundo plano (a leitura da ementa),
    # em que ninguém espera olhando a tela: na CPU, o modelo pode levar minutos
    # para processar uma parte longa antes do primeiro pedaço.
    ia_timeout_leitura_tarefas: float = 15 * 60
    # Tentativas contra o Ollama fora, só antes do primeiro pedaço: depois dele,
    # tentar de novo repetiria o texto que o aluno já viu.
    ia_tentativas: int = 2

    # Teto da mensagem do aluno, em caracteres, e quantas mensagens anteriores
    # da conversa vão como contexto para o modelo.
    chat_maximo_caracteres: int = 4000
    chat_janela_historico: int = 20

    # O refresh token vive no Redis e expira sozinho. O prazo longo é o do
    # "manter-se conectado" da tela 5; sem marcar, vale uma semana.
    refresh_token_ttl: int = 60 * 60 * 24 * 7
    refresh_token_ttl_lembrar: int = 60 * 60 * 24 * 30

    # Assina os JWT. Em produção vem do ambiente, e a aplicação não sobe sem.
    jwt_secret: str = SEGREDO_DE_DESENVOLVIMENTO
    jwt_algoritmo: str = "HS256"

    # Access token curto porque ele não é consultado no Redis a cada request:
    # é esse prazo que limita quanto tempo um logout demora a valer de fato.
    access_token_ttl: int = 15 * 60

    # Credenciais do login social. Ficam em branco por padrão; com elas em
    # branco, as rotas do provedor respondem 503 em vez de quebrar.
    github_client_id: str = ""
    github_client_secret: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""

    # Para onde o callback do OAuth devolve o aluno, no frontend.
    oauth_retorno_frontend: str = "/auth/callback"

    # Validade do link de recuperação de senha.
    reset_senha_ttl: int = 30 * 60

    # Rate limit por IP nas rotas de autenticação (#40): requisições por janela,
    # em segundos, contadas por rota. Folgado para quem erra a senha; apertado
    # para quem testa senhas em massa.
    rate_limit_auth_requisicoes: int = 20
    rate_limit_auth_janela: int = 60

    # Bloqueio depois de tentativas seguidas de login erradas no mesmo e-mail.
    # Complementa o limite por IP: pega quem troca de IP para atacar uma conta.
    bloqueio_login_tentativas: int = 5
    bloqueio_login_duracao: int = 15 * 60

    # Teto do corpo de qualquer requisição, em bytes. O maior upload previsto é
    # o PDF da ementa (o PPC); cada rota de upload aplica o seu limite, menor
    # que este.
    tamanho_maximo_requisicao: int = 35 * 1024 * 1024

    # Onde ficam os arquivos enviados pelos alunos, fora do banco. Só a
    # subpasta `avatares` é servida publicamente (em `/media/avatares`).
    diretorio_midia: str = "media"

    # Teto da foto do perfil, em bytes. Acima disso nem chega a ser aberta.
    tamanho_maximo_avatar: int = 2 * 1024 * 1024

    # Teto da ementa em PDF (#28), em bytes. O aluno costuma mandar o PPC do
    # curso, de centenas de páginas, e não há teto de páginas: só o trecho do
    # ementário vai para a IA (`services/ppc.py`).
    tamanho_maximo_ementa: int = 30 * 1024 * 1024

    # Versão dos termos de uso e da política de privacidade. Mudar a versão é o
    # que faz um consentimento antigo deixar de valer.
    versao_termos: str = "2026-09-29"

    # Dias entre o pedido de exclusão da conta e o expurgo dos dados. Entrar de
    # novo nesse prazo cancela a exclusão.
    prazo_exclusao_dias: int = 30

    @model_validator(mode="after")
    def _conferir_segredo(self) -> "Settings":
        """Impede subir em produção sem um segredo próprio.

        Um JWT assinado com segredo público — ou vazio — é um token que qualquer
        um falsifica. Melhor não subir do que subir aberto.

        O `.env.example` traz `JWT_SECRET=` em branco, então vazio conta como
        "não definido": em desenvolvimento vira o segredo de desenvolvimento, em
        produção derruba o boot.
        """
        if not self.jwt_secret.strip():
            self.jwt_secret = SEGREDO_DE_DESENVOLVIMENTO

        # Curto também não serve: HS256 com segredo pequeno cai em força bruta
        # offline a partir de um único token capturado.
        if self.environment == "production" and (
            self.jwt_secret == SEGREDO_DE_DESENVOLVIMENTO or len(self.jwt_secret) < 32
        ):
            raise ValueError(
                "Defina JWT_SECRET com pelo menos 32 caracteres: em produção o segredo de "
                "desenvolvimento não é aceito"
            )

        # O CORS libera credenciais (`allow_credentials`), e curinga com
        # credenciais entrega a API para qualquer site que o aluno abrir.
        if self.environment == "production" and "*" in self.frontend_origin:
            raise ValueError("FRONTEND_ORIGIN não pode ter '*' em produção")

        if self.ia_provedor not in PROVEDORES_DE_IA:
            raise ValueError(f"IA_PROVEDOR precisa ser um de: {', '.join(PROVEDORES_DE_IA)}")
        # O `eco` devolve a pergunta do aluno: em produção, seria um chat que
        # finge responder.
        if self.environment == "production" and self.ia_provedor != "ollama":
            raise ValueError("Em produção, IA_PROVEDOR precisa ser 'ollama'")
        return self


settings = Settings()
