"""Qual modelo atende cada uso: o chat e o trabalho em segundo plano."""

import pytest

from app.core.config import settings
from app.ia import provedor
from app.ia.ollama import Ollama


@pytest.fixture(autouse=True)
def com_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ia_provedor", "ollama")
    monkeypatch.setattr(settings, "ollama_modelo", "llama3.2")


def test_tarefas_usam_o_modelo_delas_e_o_chat_o_dele(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ollama_modelo_tarefas", "llama3.2:1b")

    chat = provedor.get_provedor_ia()
    tarefas = provedor.get_provedor_ia_tarefas()

    assert isinstance(chat, Ollama) and isinstance(tarefas, Ollama)
    assert (chat.modelo, tarefas.modelo) == ("llama3.2", "llama3.2:1b")
    # O prazo de cada um continua o seu.
    assert tarefas.timeout.read == settings.ia_timeout_leitura_tarefas


def test_sem_modelo_das_tarefas_usa_o_do_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ollama_modelo_tarefas", "")

    assert provedor.get_provedor_ia_tarefas().modelo == "llama3.2"
