"""Qual provedor atende a aplicação, conforme `IA_PROVEDOR`."""

from app.core.config import settings
from app.ia.base import ProvedorIA
from app.ia.eco import Eco
from app.ia.ollama import Ollama


def get_provedor_ia() -> ProvedorIA:
    """Dependência do FastAPI. Os testes trocam por um provedor deles."""
    if settings.ia_provedor == "eco":
        return Eco()
    return Ollama(
        settings.ollama_url,
        settings.ollama_modelo,
        modelo_embedding=settings.ollama_modelo_embedding,
        timeout_conexao=settings.ia_timeout_conexao,
        timeout_leitura=settings.ia_timeout_leitura,
        tentativas=settings.ia_tentativas,
    )
