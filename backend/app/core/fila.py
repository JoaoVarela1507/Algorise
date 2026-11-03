"""Fila do trabalho longo: a leitura da ementa agora, a transcrição dos vídeos depois.

Quem enfileira fala com `Fila`, nunca com o RQ direto. São duas implementações,
escolhidas por `FILA`:

- **`redis`** (`FilaRedis`): põe a tarefa na fila do RQ, e o serviço `worker`
  do compose a executa, fora do processo da API. Um deploy ou uma queda da API
  não perde o trabalho, e a tarefa que cai no meio é tentada de novo;
- **`local`** (`FilaLocal`): roda a tarefa no próprio processo da API, depois da
  resposta (`BackgroundTasks`). É o que os testes, a CI e o E2E usam, e o que
  deixa rodar o backend sem o worker.

A tarefa tem uma chave (`ementa-12`, `video-abc`): enquanto houver uma na fila
ou rodando com a mesma chave, um pedido novo não cria outra. É o que impede o
aluno de, clicando duas vezes em "tentar de novo", pôr duas leituras do mesmo
PPC para o modelo.
"""

import logging
import re
from collections.abc import Callable
from typing import Protocol

from fastapi import BackgroundTasks, Depends
from redis import Redis
from rq import Callback, Queue, Retry
from rq.exceptions import NoSuchJobError
from rq.job import Job, JobStatus
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.database import get_fabrica_de_sessoes
from app.ia import ProvedorIA, get_provedor_ia_tarefas

logger = logging.getLogger(__name__)

# Uma leitura de PPC na CPU passa de meia hora; o padrão do RQ, três minutos.
TEMPO_MAXIMO_DA_EMENTA = 2 * 60 * 60
# A busca de uma disciplina: algumas chamadas à API e embeddings de títulos.
TEMPO_MAXIMO_DA_BUSCA = 30 * 60
# Baixar o áudio e transcrever na CPU: perto do tempo do próprio vídeo.
TEMPO_MAXIMO_DA_TRANSCRICAO = 4 * 60 * 60
# Uma chamada ao modelo com o índice da transcrição.
TEMPO_MAXIMO_DA_SEGMENTACAO = 30 * 60
# Uma chamada ao modelo por parte do vídeo.
TEMPO_MAXIMO_DA_CATEGORIZACAO = 60 * 60
# Uma chamada ao modelo com o conteúdo do módulo.
TEMPO_MAXIMO_DOS_EXERCICIOS = 30 * 60
# Desafio de código (#34): os casos rodam em sequência, cada um com o seu teto
# na sandbox. Passando disso, o job é cancelado e a execução vira `falhou`.
TEMPO_MAXIMO_DA_EXECUCAO = 5 * 60
# A tarefa que cai no meio (o worker reiniciou, o banco piscou) é tentada de
# novo, esperando cada vez mais. A falha esperada (PDF ilegível, IA fora) não
# chega aqui: a própria tarefa a grava na ementa e termina sem erro.
NOVAS_TENTATIVAS = Retry(max=2, interval=[30, 120])

# Estados em que a tarefa ainda vai rodar ou está rodando.
_PENDENTES = {
    JobStatus.QUEUED,
    JobStatus.STARTED,
    JobStatus.DEFERRED,
    JobStatus.SCHEDULED,
}


class Fila(Protocol):
    def ementa(self, ementa_id: int) -> bool:
        """Põe a leitura da ementa na fila. `False` se já havia uma pendente."""
        ...

    def busca_de_conteudo(self, disciplina: str) -> bool:
        """Põe na fila a busca de vídeos para as lacunas da disciplina (#207)."""
        ...

    def transcricao(self, video_id: int) -> bool:
        """Põe na fila a transcrição do vídeo do YouTube (#208)."""
        ...

    def segmentacao(self, video_id: int) -> bool:
        """Põe na fila o corte do vídeo transcrito em partes (#209)."""
        ...

    def categorizacao(self, video_id: int) -> bool:
        """Põe na fila a categorização das partes do vídeo (#202)."""
        ...

    def exercicios(self, geracao_id: int) -> bool:
        """Põe na fila a geração dos exercícios de um módulo (#201)."""
        ...

    def execucao(self, execucao_id: str) -> bool:
        """Põe na fila a execução do código do desafio na sandbox (#34)."""
        ...


class FilaRedis:
    def __init__(self, conexao: Redis, nome: str = "algorise") -> None:
        self.fila = Queue(nome, connection=conexao)

    def ementa(self, ementa_id: int) -> bool:
        # Importado aqui: a tarefa puxa os serviços, que puxam esta fila.
        from app.tarefas import ementa

        return self.enfileirar(
            ementa.processar,
            ementa_id,
            chave=f"ementa-{ementa_id}",
            tempo_maximo=TEMPO_MAXIMO_DA_EMENTA,
            ao_falhar=ementa.falhou,
        )

    def busca_de_conteudo(self, disciplina: str) -> bool:
        from app.tarefas import busca

        return self.enfileirar(
            busca.buscar,
            disciplina,
            chave=f"busca-{_slug(disciplina)}",
            tempo_maximo=TEMPO_MAXIMO_DA_BUSCA,
        )

    def transcricao(self, video_id: int) -> bool:
        from app.tarefas import transcricao

        return self.enfileirar(
            transcricao.transcrever,
            video_id,
            chave=f"video-{video_id}",
            tempo_maximo=TEMPO_MAXIMO_DA_TRANSCRICAO,
            ao_falhar=transcricao.falhou,
        )

    def segmentacao(self, video_id: int) -> bool:
        from app.tarefas import segmentacao

        return self.enfileirar(
            segmentacao.segmentar,
            video_id,
            chave=f"segmentacao-{video_id}",
            tempo_maximo=TEMPO_MAXIMO_DA_SEGMENTACAO,
        )

    def categorizacao(self, video_id: int) -> bool:
        from app.tarefas import categorizacao

        return self.enfileirar(
            categorizacao.categorizar,
            video_id,
            chave=f"categorizacao-{video_id}",
            tempo_maximo=TEMPO_MAXIMO_DA_CATEGORIZACAO,
        )

    def exercicios(self, geracao_id: int) -> bool:
        from app.tarefas import exercicios

        return self.enfileirar(
            exercicios.gerar,
            geracao_id,
            chave=f"exercicios-{geracao_id}",
            tempo_maximo=TEMPO_MAXIMO_DOS_EXERCICIOS,
        )

    def execucao(self, execucao_id: str) -> bool:
        from app.tarefas import execucao

        return self.enfileirar(
            execucao.executar,
            execucao_id,
            chave=f"execucao-{execucao_id}",
            tempo_maximo=TEMPO_MAXIMO_DA_EXECUCAO,
            ao_falhar=execucao.falhou,
            # Rodar o código do aluno de novo sozinho não ajuda: ele que tente.
            novas_tentativas=None,
        )

    def enfileirar(
        self,
        funcao: Callable[..., object],
        *argumentos: object,
        chave: str,
        tempo_maximo: int,
        ao_falhar: Callable[..., object] | None = None,
        novas_tentativas: Retry | None = NOVAS_TENTATIVAS,
    ) -> bool:
        """Enfileira `funcao(*argumentos)`, a menos que a tarefa `chave` esteja pendente."""
        if self._pendente(chave):
            logger.info("Tarefa %s já está na fila; o pedido novo foi ignorado", chave)
            return False
        self.fila.enqueue(
            funcao,
            *argumentos,
            job_id=chave,
            job_timeout=tempo_maximo,
            retry=novas_tentativas,
            on_failure=Callback(ao_falhar) if ao_falhar else None,
            # O resultado não interessa (a tarefa grava no banco); a falha fica
            # uma semana no registro do RQ, para `rq info` mostrar o motivo.
            result_ttl=0,
            failure_ttl=7 * 24 * 60 * 60,
        )
        return True

    def _pendente(self, chave: str) -> bool:
        try:
            tarefa = Job.fetch(chave, connection=self.fila.connection)
        except NoSuchJobError:
            return False
        return tarefa.get_status(refresh=False) in _PENDENTES


class FilaLocal:
    """Roda a tarefa no processo da API, depois da resposta."""

    def __init__(
        self, tarefas: BackgroundTasks, fabrica: sessionmaker[Session], provedor: ProvedorIA
    ) -> None:
        self.tarefas = tarefas
        self.fabrica = fabrica
        self.provedor = provedor

    def ementa(self, ementa_id: int) -> bool:
        from app.services import ementas

        self.tarefas.add_task(ementas.processar, self.fabrica, self.provedor, ementa_id)
        return True

    def busca_de_conteudo(self, disciplina: str) -> bool:
        from app.tarefas import busca

        self.tarefas.add_task(busca.buscar, disciplina)
        return True

    def transcricao(self, video_id: int) -> bool:
        from app.tarefas import transcricao

        self.tarefas.add_task(transcricao.transcrever, video_id)
        return True

    def segmentacao(self, video_id: int) -> bool:
        from app.tarefas import segmentacao

        self.tarefas.add_task(segmentacao.segmentar, video_id)
        return True

    def categorizacao(self, video_id: int) -> bool:
        from app.tarefas import categorizacao

        self.tarefas.add_task(categorizacao.categorizar, video_id)
        return True

    def exercicios(self, geracao_id: int) -> bool:
        from app.tarefas import exercicios

        self.tarefas.add_task(exercicios.gerar_com, self.fabrica, self.provedor, geracao_id)
        return True

    def execucao(self, execucao_id: str) -> bool:
        from app.tarefas import execucao

        self.tarefas.add_task(execucao.executar_com, self.fabrica, execucao_id)
        return True


class FilaImediata:
    """Roda a tarefa agora, na thread de quem chamou.

    É a fila de quem já está fora do request (uma tarefa que dispara outra) no
    modo `local`: não há `BackgroundTasks` ali, e já não há aluno esperando.
    """

    def ementa(self, ementa_id: int) -> bool:
        from app.tarefas import ementa

        ementa.processar(ementa_id)
        return True

    def busca_de_conteudo(self, disciplina: str) -> bool:
        from app.tarefas import busca

        busca.buscar(disciplina)
        return True

    def transcricao(self, video_id: int) -> bool:
        from app.tarefas import transcricao

        transcricao.transcrever(video_id)
        return True

    def segmentacao(self, video_id: int) -> bool:
        from app.tarefas import segmentacao

        segmentacao.segmentar(video_id)
        return True

    def categorizacao(self, video_id: int) -> bool:
        from app.tarefas import categorizacao

        categorizacao.categorizar(video_id)
        return True

    def exercicios(self, geracao_id: int) -> bool:
        from app.tarefas import exercicios

        exercicios.gerar(geracao_id)
        return True

    def execucao(self, execucao_id: str) -> bool:
        from app.tarefas import execucao

        execucao.executar(execucao_id)
        return True


def conexao() -> Redis:
    """Conexão própria do RQ: ele guarda bytes (pickle), e o cliente do cache decodifica texto."""
    return Redis.from_url(settings.redis_url)


def fila_das_tarefas() -> Fila:
    """A fila para uma tarefa enfileirar outra, fora do request."""
    if settings.fila == "redis":
        return FilaRedis(conexao(), settings.fila_nome)
    return FilaImediata()


def _slug(texto: str) -> str:
    """Só letras, números e hífen: o formato que o RQ aceita no id da tarefa."""
    from app.ia.skills.ler_ementa import normalizar

    return re.sub(r"\s+", "-", normalizar(texto))[:100] or "sem-nome"


def get_fila(
    tarefas: BackgroundTasks,
    fabrica: sessionmaker[Session] = Depends(get_fabrica_de_sessoes),
    provedor: ProvedorIA = Depends(get_provedor_ia_tarefas),
) -> Fila:
    """Dependência do FastAPI: a fila do modo em `FILA`."""
    if settings.fila == "redis":
        return FilaRedis(conexao(), settings.fila_nome)
    return FilaLocal(tarefas, fabrica, provedor)
