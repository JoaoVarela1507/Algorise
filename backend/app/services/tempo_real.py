"""Tempo real (#35): as conexões de WebSocket, os canais e o pub/sub no Redis.

Quem tem algo a avisar chama `publicar(canal, evento, payload)`, de qualquer
lugar: uma rota, um serviço, uma tarefa do worker. A mensagem vai para o canal
`ws:{canal}` do Redis, e cada instância da API tem um `Ouvinte` inscrito em
`ws:*` que entrega às conexões locais inscritas naquele canal. Assim duas abas
do mesmo aluno, ligadas a instâncias diferentes, recebem o mesmo evento, e
derrubar uma instância não tira os eventos das outras.

Sem Redis, ou sem ninguém ouvindo, a entrega é direta para as conexões desta
instância: com uma instância só, que é o caso do desenvolvimento, nada se perde.

O `Ouvinte` é uma thread, e não uma tarefa do asyncio, porque cada conexão pode
viver num event loop diferente (é o que o `TestClient` faz) e porque o cliente
do Redis da aplicação é síncrono. A entrega a cada conexão passa pelo
`call_soon_threadsafe` do loop dela.
"""

import asyncio
import contextlib
import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from redis import RedisError
from sqlalchemy.orm import Session

from app.core import redis as nucleo_redis
from app.core.config import settings
from app.models import Conversa, Trilha
from app.schemas.tempo_real import Evento

logger = logging.getLogger(__name__)

PREFIXO = "ws:"
# Teto da fila de saída de cada conexão. Um cliente que não lê não pode fazer
# a memória da API crescer sem fim: passando disso, a mensagem nova é descartada.
TAMANHO_DA_FILA = 1000
# De quanto em quanto tempo o ouvinte confere se deve parar.
ESPERA_DO_OUVINTE = 0.2


@dataclass(eq=False)
class Conexao:
    """Uma aba aberta. As mensagens saem pela `fila`, lida por um escritor só."""

    usuario_id: int
    loop: asyncio.AbstractEventLoop
    fila: asyncio.Queue[dict[str, Any]] = field(
        default_factory=lambda: asyncio.Queue(TAMANHO_DA_FILA)
    )
    canais: set[str] = field(default_factory=set)
    ultimo_sinal: float = field(default_factory=time.monotonic)

    def enviar(self, mensagem: dict[str, Any]) -> None:
        """Põe na fila. Chamado no loop da própria conexão."""
        try:
            self.fila.put_nowait(mensagem)
        except asyncio.QueueFull:
            logger.warning(
                "Fila do WebSocket cheia, mensagem descartada (usuário %s)", self.usuario_id
            )

    def entregar(self, mensagem: dict[str, Any]) -> None:
        """Põe na fila a partir de outra thread."""
        # O loop já fechado é a conexão saindo; ela será removida.
        with contextlib.suppress(RuntimeError):
            self.loop.call_soon_threadsafe(self.enviar, mensagem)


class Gerenciador:
    """As conexões desta instância, por aluno e por canal."""

    def __init__(self) -> None:
        self._trava = threading.Lock()
        self._por_usuario: dict[int, set[Conexao]] = {}
        self._por_canal: dict[str, set[Conexao]] = {}

    def registrar(self, conexao: Conexao) -> bool:
        """`False` se o aluno já tem o máximo de abas abertas aqui."""
        with self._trava:
            abertas = self._por_usuario.setdefault(conexao.usuario_id, set())
            if len(abertas) >= settings.ws_conexoes_por_usuario:
                return False
            abertas.add(conexao)
            return True

    def remover(self, conexao: Conexao) -> None:
        with self._trava:
            for canal in conexao.canais:
                inscritos = self._por_canal.get(canal)
                if inscritos is not None:
                    inscritos.discard(conexao)
                    if not inscritos:
                        del self._por_canal[canal]
            conexao.canais.clear()
            abertas = self._por_usuario.get(conexao.usuario_id)
            if abertas is not None:
                abertas.discard(conexao)
                if not abertas:
                    del self._por_usuario[conexao.usuario_id]

    def inscrever(self, conexao: Conexao, canal: str) -> None:
        with self._trava:
            self._por_canal.setdefault(canal, set()).add(conexao)
            conexao.canais.add(canal)

    def cancelar(self, conexao: Conexao, canal: str) -> None:
        with self._trava:
            inscritos = self._por_canal.get(canal)
            if inscritos is not None:
                inscritos.discard(conexao)
                if not inscritos:
                    del self._por_canal[canal]
            conexao.canais.discard(canal)

    def entregar_local(self, canal: str, mensagem: dict[str, Any]) -> int:
        with self._trava:
            inscritos = list(self._por_canal.get(canal, ()))
        for conexao in inscritos:
            conexao.entregar(mensagem)
        return len(inscritos)

    def conexoes_de(self, usuario_id: int) -> int:
        with self._trava:
            return len(self._por_usuario.get(usuario_id, ()))


class Ouvinte:
    """Thread inscrita em `ws:*` no Redis, que repassa ao `Gerenciador`.

    Sobe na primeira conexão (`garantir`) e se reinscreve sozinha, com espera
    crescente, quando o Redis cai.
    """

    def __init__(self, gerenciador: Gerenciador) -> None:
        self._gerenciador = gerenciador
        self._trava = threading.Lock()
        self._thread: threading.Thread | None = None
        self._parar = threading.Event()
        self.inscrito = threading.Event()

    def garantir(self) -> None:
        with self._trava:
            if self._thread is not None and self._thread.is_alive():
                return
            self._parar.clear()
            self._thread = threading.Thread(target=self._rodar, name="ouvinte-ws", daemon=True)
            self._thread.start()

    def parar(self) -> None:
        with self._trava:
            self._parar.set()
            thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout=5)
        self.inscrito.clear()

    def _rodar(self) -> None:
        espera = 1.0
        while not self._parar.is_set():
            pubsub = None
            try:
                pubsub = nucleo_redis.cliente.pubsub(ignore_subscribe_messages=True)
                pubsub.psubscribe(f"{PREFIXO}*")
                self.inscrito.set()
                espera = 1.0
                while not self._parar.is_set():
                    recebida = pubsub.get_message(timeout=ESPERA_DO_OUVINTE)
                    if recebida and recebida.get("type") == "pmessage":
                        canal = str(recebida["channel"]).removeprefix(PREFIXO)
                        self._gerenciador.entregar_local(canal, json.loads(recebida["data"]))
            except (RedisError, OSError, ValueError) as erro:
                logger.warning("Ouvinte do WebSocket sem Redis, tentando de novo: %s", erro)
            finally:
                self.inscrito.clear()
                if pubsub is not None:
                    with contextlib.suppress(RedisError, OSError):
                        pubsub.close()
            self._parar.wait(espera)
            espera = min(espera * 2, 30.0)


gerenciador = Gerenciador()
ouvinte = Ouvinte(gerenciador)


def publicar(canal: str, evento: str, payload: dict[str, Any] | None = None) -> None:
    """Avisa todo mundo inscrito em `canal`, em qualquer instância da API.

    Se o Redis está fora, ou ninguém está inscrito no pub/sub (`PUBLISH`
    devolve 0), a entrega é direta às conexões desta instância.
    """
    mensagem = Evento(canal=canal, evento=evento, payload=payload or {}).model_dump(mode="json")
    entregues = nucleo_redis.executar(
        lambda r: r.publish(f"{PREFIXO}{canal}", json.dumps(mensagem)), padrao=None
    )
    if not entregues:
        gerenciador.entregar_local(canal, mensagem)


def pode_ouvir(db: Session, usuario_id: int, canal: str) -> bool:
    """O aluno pode se inscrever neste canal?"""
    tipo, _, chave = canal.partition(":")
    if tipo == "notificacoes":
        return chave == str(usuario_id)
    if tipo == "ranking":
        return chave == "geral" or (chave.isdigit() and db.get(Trilha, int(chave)) is not None)
    if tipo == "chat":
        if not chave.isdigit():
            return False
        conversa = db.get(Conversa, int(chave))
        return conversa is not None and conversa.usuario_id == usuario_id
    return False


class LimiteDeMensagens:
    """Janela deslizante de mensagens recebidas por conexão."""

    def __init__(self, limite: int, janela: float) -> None:
        self._limite = limite
        self._janela = janela
        self._momentos: deque[float] = deque()

    def permitir(self) -> bool:
        agora = time.monotonic()
        while self._momentos and agora - self._momentos[0] > self._janela:
            self._momentos.popleft()
        if len(self._momentos) >= self._limite:
            return False
        self._momentos.append(agora)
        return True
