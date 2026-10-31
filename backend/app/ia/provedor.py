"""Qual provedor atende a aplicação, conforme `IA_PROVEDOR`."""

from app.core.config import settings
from app.ia.base import ProvedorIA
from app.ia.eco import Eco
from app.ia.ollama import Ollama


def get_provedor_ia() -> ProvedorIA:
    """Dependência do FastAPI. Os testes trocam por um provedor deles."""
    return _provedor(settings.ia_timeout_leitura)


def get_provedor_ia_tarefas() -> ProvedorIA:
    """O provedor do trabalho em segundo plano, com `IA_TIMEOUT_LEITURA_TAREFAS`.

    O do chat desiste em dois minutos porque o aluno está esperando; a leitura
    da ementa roda depois da resposta, e na CPU uma parte longa passa disso.
    """
    return _provedor(settings.ia_timeout_leitura_tarefas)


def _provedor(timeout_leitura: float) -> ProvedorIA:
    if settings.ia_provedor == "eco":
        return Eco()
    return Ollama(
        settings.ollama_url,
        settings.ollama_modelo,
        modelo_embedding=settings.ollama_modelo_embedding,
        timeout_conexao=settings.ia_timeout_conexao,
        timeout_leitura=timeout_leitura,
        tentativas=settings.ia_tentativas,
    )
