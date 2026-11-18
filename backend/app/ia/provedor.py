"""Qual provedor atende a aplicação, conforme `IA_PROVEDOR`.

Com o Gemini, o provedor é montado por uso (`app/ia/reserva.py`): cada uso da IA
tem o seu modelo (`GEMINI_MODELOS`), com o Ollama de reserva (`IA_RESERVA`), e os
embeddings podem vir de outro provedor (`IA_PROVEDOR_EMBEDDINGS`).
"""

import logging

from app.core.config import settings
from app.ia.base import ProvedorIA
from app.ia.eco import Eco
from app.ia.gemini import Gemini
from app.ia.ollama import Ollama
from app.ia.reserva import ComReserva, PorUso

logger = logging.getLogger(__name__)


def get_provedor_ia() -> ProvedorIA:
    """Dependência do FastAPI. Os testes trocam por um provedor deles."""
    return _montar("chat", settings.ia_timeout_leitura)


def get_provedor_ia_tarefas() -> ProvedorIA:
    """O provedor do trabalho em segundo plano.

    Usa `IA_TIMEOUT_LEITURA_TAREFAS`: o chat desiste em dois minutos porque o
    aluno está esperando; a leitura da ementa roda depois da resposta, e na CPU
    uma parte longa passa disso. No Ollama, o modelo é o `OLLAMA_MODELO_TAREFAS`
    (o do chat, se vazio); no Gemini, o de cada uso.
    """
    return _montar("tarefas", settings.ia_timeout_leitura_tarefas)


def _montar(uso_padrao: str, timeout_leitura: float) -> ProvedorIA:
    if settings.ia_provedor == "eco":
        return Eco()
    if settings.ia_provedor == "ollama":
        return _ollama(_modelo_ollama(uso_padrao), timeout_leitura)

    embeddings = (
        _ollama(settings.ollama_modelo, timeout_leitura)
        if settings.ia_provedor_embeddings == "ollama"
        else _gemini(settings.gemini_modelo, timeout_leitura)
    )

    def do_uso(uso: str) -> ProvedorIA:
        modelo = settings.modelo_gemini(uso)
        principal = _gemini(modelo, timeout_leitura)
        if settings.ia_reserva != "ollama":
            return principal
        reserva = _ollama(_modelo_ollama(uso), timeout_leitura)
        return ComReserva(
            principal, reserva, nome=modelo, pausa_segundos=settings.ia_pausa_apos_falha
        )

    # "tarefas" não é um uso: quem roda em segundo plano pede o seu com `para`.
    return PorUso(do_uso, embeddings, uso_padrao="chat" if uso_padrao == "tarefas" else uso_padrao)


def _modelo_ollama(uso: str) -> str:
    if uso == "chat":
        return settings.ollama_modelo
    return settings.ollama_modelo_tarefas or settings.ollama_modelo


def _gemini(modelo: str, timeout_leitura: float) -> Gemini:
    return Gemini(
        settings.gemini_api_key,
        modelo,
        modelo_embedding=settings.gemini_modelo_embedding,
        raciocinio=settings.gemini_raciocinio,
        # Na sobrecarga, primeiro outro modelo do Gemini (rápido); só se ele
        # também falhar o pedido vai ao Ollama, que na CPU é bem mais lento.
        modelo_reserva=settings.gemini_modelo_reserva
        if settings.gemini_modelo_reserva != modelo
        else "",
        # A rede até o Google é mais lenta de abrir que a do Ollama no compose.
        timeout_conexao=max(settings.ia_timeout_conexao, 10),
        timeout_leitura=timeout_leitura,
        # Na camada gratuita um 429 passageiro é comum: uma tentativa a mais,
        # quando não há reserva para onde ir.
        tentativas=settings.ia_tentativas + (0 if settings.ia_reserva == "ollama" else 1),
    )


def _ollama(modelo: str, timeout_leitura: float) -> Ollama:
    return Ollama(
        settings.ollama_url,
        modelo,
        modelo_embedding=settings.ollama_modelo_embedding,
        timeout_conexao=settings.ia_timeout_conexao,
        timeout_leitura=timeout_leitura,
        tentativas=settings.ia_tentativas,
        manter_carregado=settings.ollama_manter_carregado,
    )


async def aquecer_reserva() -> None:
    """Carrega o modelo de reserva do chat no Ollama, para a primeira troca ser rápida.

    Só com `IA_RESERVA=ollama` e `OLLAMA_MANTER_CARREGADO`. Falhar aqui não impede
    a API de subir: o Ollama pode nem estar ligado, e a reserva é só reserva.
    """
    if settings.ia_reserva != "ollama" or not settings.ollama_manter_carregado:
        return
    try:
        await _ollama(settings.ollama_modelo, settings.ia_timeout_leitura).aquecer()
        logger.info("Modelo de reserva %s carregado no Ollama", settings.ollama_modelo)
    except Exception as erro:  # qualquer falha aqui só vira aviso
        logger.warning("Não deu para carregar o modelo de reserva no Ollama: %s", erro)
