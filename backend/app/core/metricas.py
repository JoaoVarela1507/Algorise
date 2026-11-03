"""Métricas no formato do Prometheus, em `GET /metrics` (#39).

- `algorise_requisicoes_segundos`: latência por método, rota e status. A rota é
  o modelo (`/api/v1/trilhas/{slug}`), não o caminho, para um id não virar uma
  série nova a cada aluno;
- `algorise_erros_total`: respostas 5xx por rota;
- `algorise_ia_segundos`: tempo das chamadas ao provedor de IA, por operação
  (`gerar`, `embeddings`) e resultado;
- `algorise_fila_tarefas`: tarefas esperando na fila do RQ, lidas na hora da
  coleta. Fica fora com `FILA=local`, em que não há fila.

Com `METRICAS_TOKEN`, a rota pede `Authorization: Bearer <token>`: as métricas
dizem quais rotas existem e quanto cada uma demora.
"""

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager

from prometheus_client import CollectorRegistry, Counter, Histogram
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import Collector

logger = logging.getLogger(__name__)

registro = CollectorRegistry()

requisicoes = Histogram(
    "algorise_requisicoes_segundos",
    "Latência das requisições HTTP",
    ["metodo", "rota", "status"],
    registry=registro,
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
erros = Counter("algorise_erros_total", "Respostas 5xx", ["metodo", "rota"], registry=registro)
ia = Histogram(
    "algorise_ia_segundos",
    "Tempo das chamadas ao provedor de IA",
    ["operacao", "resultado"],
    registry=registro,
    # A IA na CPU leva de segundos a minutos.
    buckets=(0.5, 1, 2.5, 5, 10, 30, 60, 120, 300, 900),
)


def observar_requisicao(metodo: str, rota: str, status: int, segundos: float) -> None:
    requisicoes.labels(metodo, rota, str(status)).observe(segundos)
    if status >= 500:
        erros.labels(metodo, rota).inc()


@contextmanager
def medir_ia(operacao: str) -> Iterator[None]:
    """Mede um bloco de chamada à IA; o resultado é `ok` ou `erro`."""
    inicio = time.perf_counter()
    resultado = "erro"
    try:
        yield
        resultado = "ok"
    finally:
        ia.labels(operacao, resultado).observe(time.perf_counter() - inicio)


class ColetorDaFila(Collector):
    """O tamanho da fila do RQ, perguntado ao Redis só quando alguém coleta."""

    def collect(self) -> Iterator[GaugeMetricFamily]:
        from app.core.config import settings

        if settings.fila != "redis":
            return
        try:
            from rq import Queue

            from app.core.fila import conexao

            tamanho = Queue(settings.fila_nome, connection=conexao()).count
        except Exception:
            logger.warning("Não deu para ler o tamanho da fila", exc_info=True)
            return
        metrica = GaugeMetricFamily("algorise_fila_tarefas", "Tarefas esperando na fila")
        metrica.add_metric([], tamanho)
        yield metrica


registro.register(ColetorDaFila())
