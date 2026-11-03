"""`WS /api/v1/ws`: a conexão de tempo real do aluno (#35).

O contrato das mensagens está em `app/schemas/tempo_real.py`, e o pub/sub em
`app/services/tempo_real.py`. Os códigos de fechamento:

| Código | Quando                                                               |
| ------ | -------------------------------------------------------------------- |
| 4401   | sem `autenticar` válido no prazo, ou o token venceu: renove e volte  |
| 4408   | a conexão ficou calada por mais que `WS_TEMPO_MORTO`                 |
| 4429   | o aluno já tem `WS_CONEXOES_POR_USUARIO` abas abertas nesta instância |
"""

import asyncio
import contextlib
import time
from collections.abc import Awaitable, Callable
from typing import Any

import anyio
from anyio.abc import TaskGroup
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.database import get_fabrica_de_sessoes
from app.core.seguranca import TokenInvalido, decodificar
from app.models import Usuario
from app.schemas.tempo_real import (
    Autenticado,
    Autenticar,
    Cancelado,
    Cancelar,
    ErroDoWebSocket,
    Inscrever,
    Inscrito,
    MensagemDoCliente,
    Ping,
    PingDoServidor,
    PongDoServidor,
)
from app.services.tempo_real import Conexao, LimiteDeMensagens, gerenciador, ouvinte, pode_ouvir

router = APIRouter(tags=["tempo-real"])

NAO_AUTENTICADO = 4401
CONEXAO_MORTA = 4408
CONEXOES_DEMAIS = 4429

type Fabrica = sessionmaker[Session]


class Fechar(Exception):
    def __init__(self, codigo: int, code: str, message: str) -> None:
        self.codigo, self.code, self.message = codigo, code, message


@router.websocket("/ws")
async def gateway(websocket: WebSocket, fabrica: Fabrica = Depends(get_fabrica_de_sessoes)) -> None:
    await websocket.accept()
    try:
        usuario_id, expira = await _autenticar(websocket, fabrica)
    except Fechar as motivo:
        await _fechar(websocket, motivo)
        return

    conexao = Conexao(usuario_id=usuario_id, loop=asyncio.get_running_loop())
    if not gerenciador.registrar(conexao):
        await _fechar(
            websocket,
            Fechar(CONEXOES_DEMAIS, "conexoes_demais", "Abas demais abertas ao mesmo tempo"),
        )
        return
    ouvinte.garantir()
    conexao.enviar(Autenticado(usuario_id=usuario_id).model_dump())

    sessao = _Sessao(websocket, conexao, fabrica, expira)
    motivo: Fechar | None = None

    async def correr(laco: Callable[[], Awaitable[None]], grupo: TaskGroup) -> None:
        # O primeiro laço que termina (aba fechada, conexão morta, token vencido)
        # encerra os outros dois.
        nonlocal motivo
        try:
            await laco()
        except Fechar as erro:
            motivo = erro
        grupo.cancel_scope.cancel()

    try:
        async with anyio.create_task_group() as grupo:
            for laco in (sessao.receber, sessao.escrever, sessao.vigiar):
                grupo.start_soon(correr, laco, grupo)
        if motivo is not None:
            await _fechar(websocket, motivo)
    finally:
        gerenciador.remover(conexao)


class _Sessao:
    """Os três laços de uma conexão autenticada."""

    def __init__(
        self, websocket: WebSocket, conexao: Conexao, fabrica: Fabrica, expira: float
    ) -> None:
        self.websocket = websocket
        self.conexao = conexao
        self.fabrica = fabrica
        self.expira = expira
        self.limite = LimiteDeMensagens(
            settings.ws_mensagens_por_janela, settings.ws_janela_segundos
        )

    async def receber(self) -> None:
        try:
            while True:
                texto = await self.websocket.receive_text()
                self.conexao.ultimo_sinal = time.monotonic()
                if not self.limite.permitir():
                    self._erro("rate_limit", "Mensagens demais; espere alguns segundos")
                    continue
                try:
                    mensagem = MensagemDoCliente.model_validate_json(texto).root
                except ValidationError:
                    self._erro("mensagem_invalida", "Mensagem fora do contrato")
                    continue
                await self._tratar(mensagem)
        except WebSocketDisconnect:
            return

    async def _tratar(self, mensagem: Any) -> None:
        if isinstance(mensagem, Inscrever):
            permitido = await run_in_threadpool(
                _pode_ouvir, self.fabrica, self.conexao.usuario_id, mensagem.canal
            )
            if not permitido:
                self._erro("canal_negado", f"Sem acesso ao canal {mensagem.canal}")
                return
            gerenciador.inscrever(self.conexao, mensagem.canal)
            self.conexao.enviar(Inscrito(canal=mensagem.canal).model_dump())
        elif isinstance(mensagem, Cancelar):
            gerenciador.cancelar(self.conexao, mensagem.canal)
            self.conexao.enviar(Cancelado(canal=mensagem.canal).model_dump())
        elif isinstance(mensagem, Ping):
            self.conexao.enviar(PongDoServidor().model_dump())
        elif isinstance(mensagem, Autenticar):
            # Token renovado no meio da conexão: estende o prazo, sem reconectar.
            usuario_id, expira = await _validar(mensagem.token, self.fabrica)
            if usuario_id != self.conexao.usuario_id:
                raise Fechar(NAO_AUTENTICADO, "nao_autenticado", "Token de outro usuário")
            self.expira = expira
            self.conexao.enviar(Autenticado(usuario_id=usuario_id).model_dump())
        # `pong` só conta como sinal de vida, já anotado em `receber`.

    async def escrever(self) -> None:
        """O único que escreve no socket: tudo passa pela fila da conexão."""
        while True:
            mensagem = await self.conexao.fila.get()
            try:
                await self.websocket.send_json(mensagem)
            except (WebSocketDisconnect, RuntimeError):
                return

    async def vigiar(self) -> None:
        """Ping periódico, conexão morta e token vencido."""
        while True:
            await asyncio.sleep(settings.ws_intervalo_ping)
            if time.monotonic() - self.conexao.ultimo_sinal > settings.ws_tempo_morto:
                raise Fechar(CONEXAO_MORTA, "conexao_morta", "Sem resposta ao ping")
            if time.time() >= self.expira:
                raise Fechar(NAO_AUTENTICADO, "token_expirado", "Sessão expirada; renove o token")
            self.conexao.enviar(PingDoServidor().model_dump())

    def _erro(self, code: str, message: str) -> None:
        self.conexao.enviar(ErroDoWebSocket(code=code, message=message).model_dump())


async def _autenticar(websocket: WebSocket, fabrica: Fabrica) -> tuple[int, float]:
    """O primeiro frame precisa ser `autenticar`, dentro do prazo."""
    try:
        texto = await asyncio.wait_for(
            websocket.receive_text(), timeout=settings.ws_tempo_para_autenticar
        )
        mensagem = MensagemDoCliente.model_validate_json(texto).root
    except TimeoutError as erro:
        raise Fechar(
            NAO_AUTENTICADO, "nao_autenticado", "Autenticação não chegou a tempo"
        ) from erro
    except ValidationError as erro:
        raise Fechar(NAO_AUTENTICADO, "nao_autenticado", "Primeiro frame inválido") from erro
    if not isinstance(mensagem, Autenticar):
        raise Fechar(NAO_AUTENTICADO, "nao_autenticado", "O primeiro frame deve ser autenticar")
    return await _validar(mensagem.token, fabrica)


async def _validar(token: str, fabrica: Fabrica) -> tuple[int, float]:
    try:
        conteudo = decodificar(token, tipo="access")
    except TokenInvalido as erro:
        raise Fechar(NAO_AUTENTICADO, "nao_autenticado", "Token inválido ou expirado") from erro
    usuario_id = int(conteudo["sub"])
    if not await run_in_threadpool(_conta_ativa, fabrica, usuario_id):
        raise Fechar(NAO_AUTENTICADO, "nao_autenticado", "Conta inexistente ou em exclusão")
    return usuario_id, float(conteudo["exp"])


def _conta_ativa(fabrica: Fabrica, usuario_id: int) -> bool:
    with fabrica() as db:
        usuario = db.get(Usuario, usuario_id)
        return usuario is not None and usuario.exclusao_agendada_para is None


def _pode_ouvir(fabrica: Fabrica, usuario_id: int, canal: str) -> bool:
    with fabrica() as db:
        return pode_ouvir(db, usuario_id, canal)


async def _fechar(websocket: WebSocket, motivo: Fechar) -> None:
    with contextlib.suppress(WebSocketDisconnect, RuntimeError):
        await websocket.send_json(
            ErroDoWebSocket(code=motivo.code, message=motivo.message).model_dump()
        )
        await websocket.close(code=motivo.codigo)
