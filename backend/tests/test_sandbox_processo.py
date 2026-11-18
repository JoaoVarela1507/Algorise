"""Modo `processo` da sandbox: o desafio rodando sem Docker (#25).

Roda o Python de verdade, então os testes são poucos e rápidos: o prazo vai a
1 segundo e o teto da saída a poucos kB.
"""

import pytest

from app.core.config import Settings, settings
from app.sandbox import executar


@pytest.fixture(autouse=True)
def modo_processo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "sandbox_modo", "processo")
    monkeypatch.setattr(settings, "sandbox_tempo_segundos", 1)
    monkeypatch.setattr(settings, "sandbox_saida_maxima", 4096)


def test_le_a_entrada_e_devolve_a_saida() -> None:
    resultado = executar("print(sum(int(l) for l in open(0).read().split()))", "2\n3\n")

    assert resultado.codigo_saida == 0
    assert resultado.stdout.strip() == "5"
    assert not resultado.tempo_esgotado


def test_erro_do_aluno_vem_no_stderr() -> None:
    resultado = executar("1 / 0")

    assert resultado.codigo_saida != 0
    assert "ZeroDivisionError" in resultado.stderr


def test_loop_infinito_e_cortado_no_prazo() -> None:
    resultado = executar("while True:\n    pass")

    assert resultado.tempo_esgotado


def test_saida_sem_fim_e_cortada() -> None:
    resultado = executar("while True:\n    print('x' * 100)")

    assert resultado.saida_cortada
    assert len(resultado.stdout) <= 4096


def test_variaveis_da_api_nao_chegam_ao_aluno(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "segredo")

    resultado = executar("import os\nprint(os.environ.get('GEMINI_API_KEY'))")

    assert resultado.stdout.strip() == "None"


def test_producao_recusa_o_modo_processo() -> None:
    with pytest.raises(ValueError, match="SANDBOX_MODO"):
        Settings(
            environment="production", jwt_secret="s" * 40, fila="redis", sandbox_modo="processo"
        )
    with pytest.raises(ValueError, match="SANDBOX_MODO"):
        Settings(sandbox_modo="qualquer")
    assert Settings(sandbox_modo="processo").sandbox_modo == "processo"
