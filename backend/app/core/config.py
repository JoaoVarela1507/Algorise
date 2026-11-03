from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app import __version__

# Vale para desenvolvimento e para os testes; em produção a aplicação se recusa
# a subir com ele (ver `_conferir_segredo`).
SEGREDO_DE_DESENVOLVIMENTO = "inseguro-so-para-desenvolvimento"

PROVEDORES_DE_IA = ("ollama", "eco")
MODOS_DA_FILA = ("local", "redis")
FORMATOS_DE_LOG = ("json", "texto")


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

    # WebSocket (#35). O token vem no primeiro frame, dentro do prazo; o servidor
    # manda `ping` a cada intervalo e derruba a conexão calada por mais tempo
    # que `ws_tempo_morto`. Os limites são por instância da API.
    ws_tempo_para_autenticar: float = 10
    ws_intervalo_ping: float = 25
    ws_tempo_morto: float = 60
    ws_conexoes_por_usuario: int = 5
    ws_mensagens_por_janela: int = 30
    ws_janela_segundos: float = 10
    # De quanto em quanto tempo o ranking em tempo real é publicado (#37): os
    # pontos do intervalo saem juntos, num evento por ranking.
    ranking_intervalo_ao_vivo: float = 2

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

    # Onde roda o trabalho longo (a leitura da ementa, depois a transcrição dos
    # vídeos), ver `app/core/fila.py`. `redis` põe na fila do RQ, que o serviço
    # `worker` consome; `local` roda no próprio processo da API, depois da
    # resposta, e serve para os testes, a CI, o E2E e para rodar sem o worker.
    fila: str = "local"
    # Nome da fila no RQ: o worker escuta esta.
    fila_nome: str = "algorise"

    # Busca de vídeos para as lacunas das ementas (#207), pela YouTube Data API
    # v3. Sem a chave, a busca fica desligada e as lacunas esperam em `pendente`.
    youtube_api_key: str = ""
    # Unidades por dia que a busca pode gastar. A cota do Google é de 10 mil, e
    # uma busca custa 100; a folga fica para quem testar pelo console.
    youtube_cota_diaria: int = 9000
    # Duração aceita de um vídeo avulso, em segundos: abaixo, é um corte sem
    # explicação; acima, uma live que ninguém vai assistir inteira.
    youtube_duracao_minima: int = 3 * 60
    youtube_duracao_maxima: int = 3 * 60 * 60
    # Distância de cosseno máxima entre o assunto e o título do vídeo. Mais
    # folgada que a da ementa: o título é curto e diz pouco.
    youtube_distancia_maxima: float = 0.45
    # Observabilidade (#39). `json` para o agregador, `texto` para o terminal;
    # vazio, `json` em produção e `texto` no resto (ver `formato_de_log`).
    log_formato: str = ""
    log_nivel: str = "INFO"
    # Sentry: sem o DSN, a captura de exceções fica desligada.
    sentry_dsn: str = ""
    # Com valor, `GET /metrics` pede `Authorization: Bearer <token>`.
    metricas_token: str = ""

    # Transcrição dos vídeos (#208), no worker. `small` é o modelo do Whisper
    # que cabe numa CPU; `int8` reduz a memória à custa de pouca precisão.
    whisper_modelo: str = "small"
    whisper_computacao: str = "int8"
    # Vídeo mais longo que isto não é transcrito: ocuparia o worker por horas.
    transcricao_duracao_maxima: int = 3 * 60 * 60
    # Duração máxima de uma parte do vídeo, em segundos (#209). O vídeo mais
    # curto que isto vira uma parte só, sem chamar a IA.
    segmentacao_duracao_maxima: int = 25 * 60
    # Confiança mínima da IA para uma parte de vídeo entrar na trilha (#202).
    # Abaixo, a parte é descartada, como a que não é de matéria nenhuma.
    categorizacao_confianca_minima: float = 0.6
    # Quantos alunos precisam reportar o vídeo de um módulo automático para ele
    # sair da trilha e a lacuna voltar para a busca (#210).
    reportes_para_remover: int = 3

    # Fuso em que vira o dia do streak (#31): o aluno brasileiro que estuda às
    # 23h não pode perder a sequência porque o servidor está em UTC.
    fuso_horario: str = "America/Recife"
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

    @property
    def formato_de_log(self) -> str:
        return self.log_formato or ("json" if self.environment == "production" else "texto")

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

        if self.log_formato and self.log_formato not in FORMATOS_DE_LOG:
            raise ValueError(f"LOG_FORMATO precisa ser um de: {', '.join(FORMATOS_DE_LOG)}")

        if self.fila not in MODOS_DA_FILA:
            raise ValueError(f"FILA precisa ser um de: {', '.join(MODOS_DA_FILA)}")
        # Na `local`, uma leitura de minutos roda dentro do processo da API, e
        # um deploy no meio a perde sem deixar rastro.
        if self.environment == "production" and self.fila != "redis":
            raise ValueError("Em produção, FILA precisa ser 'redis'")
        return self


settings = Settings()
