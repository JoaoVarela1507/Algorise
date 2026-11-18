import json
from typing import Annotated, Any

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app import __version__

# Vale para desenvolvimento e para os testes; em produção a aplicação se recusa
# a subir com ele (ver `_conferir_segredo`).
SEGREDO_DE_DESENVOLVIMENTO = "inseguro-so-para-desenvolvimento"

PROVEDORES_DE_IA = ("ollama", "gemini", "eco")
# Cada uso da IA, para escolher um modelo por uso (`GEMINI_MODELOS`).
USOS_DA_IA = (
    "chat",
    "resumo",
    "correcao",
    "exercicios",
    "ementa",
    "categorizacao",
    "segmentacao",
)
# Um modelo do Gemini por uso: cada modelo tem a sua cota na camada gratuita
# (pedidos por minuto e por dia) e a sua fila de capacidade, então espalhar os
# usos evita que a leitura de uma ementa, por exemplo, gaste a cota do chat.
# Medido em 17/11/2026 com a chave do projeto: estes respondem JSON em 1 s
# (o gemma em 6 s, por isso só no segundo plano); os "flash" maiores davam 503
# de sobrecarga. O chat usa o `GEMINI_MODELO`; um uso fora do dicionário, o
# `GEMINI_MODELO_TAREFAS` (ou o do chat).
GEMINI_MODELOS_PADRAO = {
    "correcao": "gemini-3.1-flash-lite",
    "resumo": "gemini-flash-lite-latest",
    "exercicios": "gemini-3-flash-preview",
    "ementa": "gemini-3.1-flash-lite-preview",
    "categorizacao": "gemma-4-31b-it",
    "segmentacao": "gemma-4-31b-it",
}
MODOS_DA_FILA = ("local", "redis")
MODOS_DA_SANDBOX = ("docker", "processo", "desligada")
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
    # a invalidação é explícita (`ranking.atualizar` grava o saldo novo e
    # renova o TTL). Com 60 s, o `aquecer` relia todos os alunos a cada minuto
    # parado; uma hora basta para o que escapa da invalidação (Redis fora na
    # hora do XP, ajuste direto no banco sem `ranking.invalidar()`).
    cache_ttl_trilhas: int = 300
    cache_ttl_ranking: int = 3600

    # Teto de XP por janela, contra farm (#31). Generoso de propósito: o aluno
    # dedicado passa longe disso, e um script varrendo o catálogo esbarra.
    xp_maximo_por_janela: int = 500
    xp_janela_segundos: int = 60 * 60
    # Meta de XP do dia que a home mostra (tela 16). Alcançável com uns dois ou
    # três exercícios: a ideia é criar o hábito, não cobrar uma maratona.
    xp_meta_diaria: int = 50

    # Janela e teto do rate limit do chat, que custa chamada de IA por request.
    rate_limit_chat_requisicoes: int = 20
    rate_limit_chat_janela: int = 60

    # Sandbox do desafio de código (#34). `docker` roda cada caso de teste num
    # container efêmero; `desligada` recusa a execução (máquina sem Docker).
    # `processo` roda o Python direto na máquina, com tempo e saída limitados
    # (e memória no Linux), mas sem isolar rede nem disco: só para rodar local
    # e apresentar sem Docker. Em produção é recusado.
    # `SANDBOX_RUNTIME=runsc` usa o gVisor, que isola o kernel também: é o que
    # se quer em produção.
    sandbox_modo: str = "docker"
    sandbox_imagem: str = "python:3.13-alpine"
    sandbox_runtime: str = ""
    sandbox_memoria_mb: int = 128
    sandbox_cpus: float = 0.5
    sandbox_processos: int = 32
    sandbox_tempo_segundos: int = 5
    sandbox_saida_maxima: int = 64 * 1024
    sandbox_codigo_maximo: int = 20_000
    # Execuções por aluno por janela: cada uma sobe um container por caso.
    rate_limit_execucoes_requisicoes: int = 10
    rate_limit_execucoes_janela: int = 60

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
    # Modelo do trabalho em segundo plano (leitura da ementa, segmentação,
    # categorização e exercícios). Na CPU, um modelo menor lê a ementa de 2 a 3
    # vezes mais rápido, e ali ninguém conversa com ele. Em branco, usa o do chat.
    ollama_modelo_tarefas: str = ""
    # Embedding do vault das skills (#200). Multilíngue, porque o conteúdo é em
    # português; a dimensão dele (1024) está fixa na tabela `vault_trechos`.
    ollama_modelo_embedding: str = "bge-m3"
    # Distância de cosseno até o módulo mais próximo no vault abaixo da qual um
    # assunto da ementa conta como coberto (#38). Acima, vira lacuna. A distância
    # de cada assunto fica gravada em `ementa_assuntos.distancia`.
    #
    # Calibrado em 17/11/2026 com o `bge-m3` e o PPC de Ciência da Computação da
    # UFRPE: 40 assuntos com a resposta certa marcada à mão (24 com módulo no
    # catálogo de 9 trilhas, 16 que deviam virar lacuna). Em 0,35: 12 certos, 4
    # errados, 12 perdidos. Em 0,38: 16 certos, mas 12 errados; em 0,40, 19
    # errados. Até 0,35 a maior parte acerta; acima, o erro cresce mais rápido
    # que o acerto. Também foi testado embutir só o assunto, sem a disciplina, e
    # o assunto antes da disciplina: os dois ordenam pior que "disciplina: assunto".
    ementa_distancia_maxima: float = 0.35
    # Tamanho de cada parte da ementa mandada à IA, em caracteres, e quantas
    # partes são lidas ao mesmo tempo. 0 escolhe pelo provedor: o Ollama lê 4 mil
    # caracteres, uma parte por vez (contexto pequeno, CPU da máquina); o Gemini,
    # 12 mil, três de cada vez (ver `services/assuntos_ementa.py`).
    ementa_tamanho_da_parte: int = 0
    ementa_leituras_simultaneas: int = 0

    # Segunda opção de IA: a API do Gemini (`IA_PROVEDOR=gemini`). Mais leve que
    # o Ollama, porque o modelo roda no Google; a chave é criada de graça no
    # Google AI Studio e a camada gratuita tem limite de pedidos por minuto e
    # por dia. Os modelos são os mesmos papéis dos do Ollama: o do chat, o das
    # tarefas (em branco, o do chat) e o de embedding do vault.
    gemini_api_key: str = ""
    # `gemini-flash-lite-latest` é um apelido que o Google aponta sempre para o
    # flash-lite atual: não quebra quando uma versão é aposentada (o 2.5 já não
    # aceita chave nova). O lite é o que responde na camada gratuita sem 503.
    # As tarefas usam o do chat quando `GEMINI_MODELO_TAREFAS` está vazio.
    gemini_modelo: str = "gemini-flash-lite-latest"
    gemini_modelo_tarefas: str = ""
    # Gera vetores de 1024 posições quando pedido, a dimensão do vault. Trocar
    # de provedor de embedding pede reingerir o vault (os vetores não se
    # comparam entre modelos).
    gemini_modelo_embedding: str = "gemini-embedding-001"
    # "Raciocínio" (thinking) do modelo, que conta no teto de tokens da resposta,
    # e as skills usam tetos curtos. Nos 3.x é um nível (`minimal`, `low`,
    # `medium`, `high`); nos 2.5, um número de tokens (`0` desliga). Vazio não
    # manda nada, e o modelo decide sozinho. `minimal` é o mais rápido: medido no
    # gemini-3.5-flash-lite, o primeiro pedaço do chat sai em 1,5 s de mediana,
    # contra 9 s (e picos de 20 s) com `low`.
    gemini_raciocinio: str = "minimal"
    # Para onde o pedido vai quando o modelo segue sobrecarregado ("high demand")
    # depois das tentativas, desde que nada da resposta tenha saído ainda. Cada
    # modelo tem a sua fila de capacidade no Google. Vazio desliga.
    gemini_modelo_reserva: str = "gemini-3.1-flash-lite"
    # Modelo por uso da IA (JSON no `.env`, como `{"chat": "gemini-3.5-flash-lite"}`).
    # O que faltar vem de `GEMINI_MODELOS_PADRAO`.
    gemini_modelos: Annotated[dict[str, str], NoDecode] = {}

    # Quem gera os embeddings do vault, separado de quem conversa. Vazio usa o
    # `IA_PROVEDOR`. Com `ollama`, o vault fica no `bge-m3` da máquina, sem cota
    # nenhuma, e o Gemini fica só para gerar texto. Trocar pede reingerir o vault:
    # vetores de modelos diferentes não se comparam.
    ia_provedor_embeddings: str = ""
    # Reserva da geração de texto: quando o provedor principal falha (cota
    # esgotada, sobrecarga, fora do ar) antes de mandar qualquer pedaço, o pedido
    # vai para este. Vazio desliga. Hoje só o `ollama` faz sentido aqui.
    ia_reserva: str = ""
    # Depois de uma falha do principal, os pedidos daquele modelo vão direto
    # para a reserva por estes segundos, em vez de esperar o erro de novo a cada
    # pedido (a cota do dia, quando acaba, não volta em segundos).
    ia_pausa_apos_falha: float = 60
    # Quanto tempo o Ollama mantém o modelo carregado depois de um pedido (o
    # `keep_alive` dele, como `30m`; vazio é o padrão do Ollama, 5 minutos). Com
    # valor e `IA_RESERVA=ollama`, a API também carrega o modelo de reserva ao
    # subir: a primeira carga leva mais de um minuto nesta máquina, e a reserva
    # que demora isso na primeira falha do Gemini parece travada.
    ollama_manter_carregado: str = ""

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
    # Anexos do chat (#33): texto, código, PDF ou imagem. Só o texto vai para o
    # modelo (até `chat_anexo_texto_maximo` caracteres por anexo).
    chat_anexo_tamanho_maximo: int = 2 * 1024 * 1024
    chat_anexos_por_mensagem: int = 3
    chat_anexo_texto_maximo: int = 8000

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

    @field_validator("gemini_modelos", mode="before")
    @classmethod
    def _ler_gemini_modelos(cls, valor: Any) -> Any:
        """JSON no `.env`; vazio (o compose passa assim quando não há) é nenhum."""
        if isinstance(valor, str):
            return json.loads(valor) if valor.strip() else {}
        return valor

    def modelo_gemini(self, uso: str) -> str:
        """O modelo do Gemini para este uso da IA.

        Na ordem: o do uso em `GEMINI_MODELOS`; no chat, o `GEMINI_MODELO`; o
        padrão do uso; e, para um uso sem padrão, o das tarefas ou o do chat.
        """
        if modelo := self.gemini_modelos.get(uso):
            return modelo
        if uso == "chat":
            return self.gemini_modelo
        return GEMINI_MODELOS_PADRAO.get(uso) or self.gemini_modelo_tarefas or self.gemini_modelo

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
        for nome, valor in (
            ("IA_PROVEDOR_EMBEDDINGS", self.ia_provedor_embeddings),
            ("IA_RESERVA", self.ia_reserva),
        ):
            if valor and valor not in PROVEDORES_DE_IA:
                raise ValueError(
                    f"{nome} precisa ser vazio ou um de: {', '.join(PROVEDORES_DE_IA)}"
                )
        if desconhecidos := set(self.gemini_modelos) - set(USOS_DA_IA):
            raise ValueError(
                f"GEMINI_MODELOS tem usos desconhecidos: {', '.join(sorted(desconhecidos))}"
            )
        # O `eco` devolve a pergunta do aluno: em produção, seria um chat que
        # finge responder.
        if self.environment == "production" and self.ia_provedor == "eco":
            raise ValueError("Em produção, IA_PROVEDOR precisa ser 'ollama' ou 'gemini'")
        # Sem a chave, todo pedido ao Gemini falharia; em produção, melhor não
        # subir. Em desenvolvimento sobe, e o chat responde "IA indisponível".
        if (
            self.environment == "production"
            and self.ia_provedor == "gemini"
            and not self.gemini_api_key.strip()
        ):
            raise ValueError(
                "IA_PROVEDOR=gemini pede GEMINI_API_KEY: crie uma chave em "
                "https://aistudio.google.com/apikey"
            )

        if self.log_formato and self.log_formato not in FORMATOS_DE_LOG:
            raise ValueError(f"LOG_FORMATO precisa ser um de: {', '.join(FORMATOS_DE_LOG)}")

        if self.fila not in MODOS_DA_FILA:
            raise ValueError(f"FILA precisa ser um de: {', '.join(MODOS_DA_FILA)}")
        # Na `local`, uma leitura de minutos roda dentro do processo da API, e
        # um deploy no meio a perde sem deixar rastro.
        if self.environment == "production" and self.fila != "redis":
            raise ValueError("Em produção, FILA precisa ser 'redis'")

        if self.sandbox_modo not in MODOS_DA_SANDBOX:
            raise ValueError(f"SANDBOX_MODO precisa ser um de: {', '.join(MODOS_DA_SANDBOX)}")
        # O modo `processo` roda código de qualquer aluno sem isolamento.
        if self.environment == "production" and self.sandbox_modo == "processo":
            raise ValueError("Em produção, SANDBOX_MODO não pode ser 'processo'")
        return self


settings = Settings()
