"""A resposta do tutor pelo WebSocket (#36).

Faz o mesmo que o `POST /chat/mensagens` em SSE, que continua de fallback, mas
publica cada pedaço no canal `chat:{conversa_id}`. Assim toda aba inscrita na
conversa acompanha a mesma geração, e o "gerando" fica igual em todas.

| Evento         | Payload                                                       |
| -------------- | ------------------------------------------------------------- |
| `chat.conversa`| `conversa_id`, `titulo`, `mensagem_id`, `pergunta`: começou   |
| `chat.token`   | `texto`: mais um pedaço                                       |
| `chat.fim`     | `mensagem_id`: resposta completa e gravada                    |
| `chat.parado`  | `mensagem_id`: o aluno parou; o parcial fica gravado          |
| `chat.erro`    | `code`, `message`, `mensagem_id`: caiu no meio; parcial gravado |
| `chat.digitando` | `usuario_id`: o aluno está escrevendo em outra aba           |

O parcial fica gravado com `incompleta = true` em todo final que não é o
`chat.fim`, inclusive quando a aba que perguntou fecha: a geração anda dentro
da conexão dela e é cancelada junto.

**Parar** vale de qualquer aba e de qualquer instância da API. A instância que
gera confere uma marca no Redis (`chat:parar:{id}`) a cada pedaço. Na própria
instância, o cancelamento é imediato, e cancelar a leitura do fluxo fecha a
requisição ao provedor: o modelo para de gerar.
"""

import asyncio
import logging
import threading
from dataclasses import dataclass
from typing import Any

import anyio
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session, sessionmaker

from app.core import redis as nucleo_redis
from app.core.config import settings
from app.core.rate_limit import verificar
from app.ia import IAIndisponivel, ProvedorIA
from app.models import Usuario
from app.schemas.chat import NovaMensagem
from app.schemas.tempo_real import ErroDoWebSocket, Inscrito
from app.services import anexos, chat, resumo_chat
from app.services.tempo_real import Conexao, gerenciador, publicar

logger = logging.getLogger(__name__)

IA_FORA = "O tutor está fora do ar agora. Tente de novo em instantes."
MUITAS_MENSAGENS = "Muitas mensagens em pouco tempo. Tente de novo em instantes."
# A marca de parada vence sozinha: uma geração que já acabou não a apaga.
VALIDADE_DA_PARADA = 120

type Fabrica = sessionmaker[Session]


@dataclass
class _Geracao:
    loop: asyncio.AbstractEventLoop
    escopo: anyio.CancelScope


_trava = threading.Lock()
_geracoes: dict[int, _Geracao] = {}


def canal_da(conversa_id: int) -> str:
    return f"chat:{conversa_id}"


def em_andamento(conversa_id: int) -> bool:
    with _trava:
        return conversa_id in _geracoes


def pedir_parada(conversa_id: int) -> None:
    """Para a geração da conversa, esteja ela nesta instância ou em outra."""
    nucleo_redis.executar(
        lambda r: r.set(_chave_de_parada(conversa_id), "1", ex=VALIDADE_DA_PARADA)
    )
    with _trava:
        geracao = _geracoes.get(conversa_id)
    if geracao is not None:
        geracao.loop.call_soon_threadsafe(geracao.escopo.cancel)


async def responder(
    *, fabrica: Fabrica, provedor: ProvedorIA, remetente: Conexao, dados: NovaMensagem
) -> None:
    """Pergunta ao tutor e publica a resposta no canal da conversa."""
    usuario_id = remetente.usuario_id
    permitido = await run_in_threadpool(
        lambda: (
            verificar(
                f"chat:usuario:{usuario_id}",
                limite=settings.rate_limit_chat_requisicoes,
                janela=settings.rate_limit_chat_janela,
            ).permitido
        )
    )
    if not permitido:
        _erro(remetente, "rate_limit", MUITAS_MENSAGENS)
        return

    try:
        preparo = await run_in_threadpool(_preparar, fabrica, usuario_id, dados)
    except chat.ConversaNaoEncontrada:
        _erro(remetente, "conversa_nao_encontrada", "Conversa não encontrada")
        return
    except anexos.AnexoNaoEncontrado:
        _erro(remetente, "anexo_nao_encontrado", "Anexo não encontrado ou já usado")
        return
    except anexos.AnexoInvalido as erro:
        _erro(remetente, "anexo_invalido", str(erro))
        return

    escopo = anyio.CancelScope()
    if preparo.conversa_id is not None and not _registrar(preparo.conversa_id, escopo):
        _erro(remetente, "chat_ocupado", "O tutor ainda está respondendo nesta conversa")
        return

    fluxo = provedor.gerar(preparo.contexto, max_tokens=preparo.max_tokens)
    try:
        primeiro = await anext(fluxo, "")
    except IAIndisponivel as erro:
        logger.warning("IA indisponível antes de responder: %s", erro)
        _soltar(preparo.conversa_id)
        await fluxo.aclose()
        _erro(remetente, "ia_indisponivel", IA_FORA)
        return

    conversa_id, titulo, pergunta_id = await run_in_threadpool(
        _registrar_pergunta,
        fabrica,
        usuario_id,
        preparo.conversa_id,
        dados.conteudo,
        dados.anexo_ids,
    )
    if preparo.conversa_id is None:
        _registrar(conversa_id, escopo)
    canal = canal_da(conversa_id)
    if canal not in remetente.canais:
        # Conversa nova: quem perguntou passa a ouvir o canal dela antes do
        # primeiro evento, para não perder o começo.
        gerenciador.inscrever(remetente, canal)
        remetente.enviar(Inscrito(canal=canal).model_dump())

    await _transmitir(
        fabrica=fabrica,
        fluxo=fluxo,
        primeiro=primeiro,
        escopo=escopo,
        conversa_id=conversa_id,
        inicio={
            "conversa_id": conversa_id,
            "titulo": titulo,
            "mensagem_id": pergunta_id,
            "pergunta": dados.conteudo,
        },
    )
    # O aluno já tem a resposta: o que saiu da janela de contexto vira resumo.
    await resumo_chat.atualizar(fabrica, provedor, conversa_id)


async def _transmitir(
    *,
    fabrica: Fabrica,
    fluxo: Any,
    primeiro: str,
    escopo: anyio.CancelScope,
    conversa_id: int,
    inicio: dict[str, Any],
) -> None:
    canal = canal_da(conversa_id)
    partes: list[str] = []
    final = "erro"
    code = "ia_indisponivel"
    try:
        await run_in_threadpool(_limpar_parada, conversa_id)
        await run_in_threadpool(publicar, canal, "chat.conversa", inicio)
        with escopo:
            pedacos = [primeiro] if primeiro else []
            parar = False
            for pedaco in pedacos:
                partes.append(pedaco)
                parar = await run_in_threadpool(_publicar_pedaco, conversa_id, pedaco)
            while not parar:
                pedaco = await anext(fluxo, None)
                if pedaco is None:
                    break
                partes.append(pedaco)
                parar = await run_in_threadpool(_publicar_pedaco, conversa_id, pedaco)
            final = "parado" if parar else "fim"
        if escopo.cancelled_caught:
            final = "parado"
    except IAIndisponivel as erro:
        logger.warning("IA parou no meio da resposta: %s", erro)
    except anyio.get_cancelled_exc_class():
        # A aba que perguntou fechou: o parcial fica gravado mesmo assim.
        code = "conexao_perdida"
        raise
    finally:
        _soltar(conversa_id)
        with anyio.CancelScope(shield=True):
            await fluxo.aclose()
            resposta_id = await run_in_threadpool(
                chat.registrar_resposta,
                fabrica,
                conversa_id,
                "".join(partes),
                incompleta=final != "fim",
            )
            if final == "erro":
                payload = {"code": code, "message": IA_FORA, "mensagem_id": resposta_id}
            else:
                payload = {"mensagem_id": resposta_id}
            await run_in_threadpool(publicar, canal, f"chat.{final}", payload)


def _publicar_pedaco(conversa_id: int, pedaco: str) -> bool:
    """Publica o pedaço e diz se alguém pediu para parar."""
    publicar(canal_da(conversa_id), "chat.token", {"texto": pedaco})
    marcada = nucleo_redis.executar(lambda r: r.exists(_chave_de_parada(conversa_id)), padrao=0)
    return bool(marcada)


def _limpar_parada(conversa_id: int) -> None:
    nucleo_redis.executar(lambda r: r.delete(_chave_de_parada(conversa_id)))


def _chave_de_parada(conversa_id: int) -> str:
    return f"chat:parar:{conversa_id}"


def _registrar(conversa_id: int, escopo: anyio.CancelScope) -> bool:
    with _trava:
        if conversa_id in _geracoes:
            return False
        _geracoes[conversa_id] = _Geracao(asyncio.get_running_loop(), escopo)
        return True


def _soltar(conversa_id: int | None) -> None:
    if conversa_id is None:
        return
    with _trava:
        _geracoes.pop(conversa_id, None)


def _preparar(fabrica: Fabrica, usuario_id: int, dados: NovaMensagem) -> chat.Preparo:
    with fabrica() as db:
        usuario = db.get_one(Usuario, usuario_id)
        return chat.preparar(
            db, usuario, dados.conversa_id, dados.conteudo, dados.modo, dados.anexo_ids
        )


def _registrar_pergunta(
    fabrica: Fabrica,
    usuario_id: int,
    conversa_id: int | None,
    conteudo: str,
    anexo_ids: list[int],
) -> tuple[int, str, int]:
    with fabrica() as db:
        usuario = db.get_one(Usuario, usuario_id)
        conversa, pergunta = chat.registrar_pergunta(db, usuario, conversa_id, conteudo, anexo_ids)
        return conversa.id, conversa.titulo, pergunta.id


def _erro(remetente: Conexao, code: str, message: str) -> None:
    remetente.enviar(ErroDoWebSocket(code=code, message=message).model_dump())
