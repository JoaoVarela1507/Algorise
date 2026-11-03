"""Contenção da sandbox (#34), com o Docker de verdade.

A issue não fecha sem estes testes: são eles que mostram que o código do aluno
não sai da caixa. Rodam com `SANDBOX_TESTES=1` e o Docker disponível (o CI
liga); fora disso, são pulados.

Cada teste roda o código malicioso pela mesma função que o worker usa e confere
duas coisas: que o ataque não funcionou e que a execução voltou, com o motivo
certo, em vez de travar o worker.
"""

import os
import shutil
import time

import pytest

from app.core.config import settings
from app.sandbox import executar

pytestmark = [
    pytest.mark.sandbox,
    pytest.mark.skipif(
        os.environ.get("SANDBOX_TESTES") != "1" or shutil.which("docker") is None,
        reason="defina SANDBOX_TESTES=1, com o Docker de pé, para rodar a contenção",
    ),
]


def test_codigo_normal_roda() -> None:
    resultado = executar("print(sum(int(n) for n in input().split()))", "2 3\n")

    assert (resultado.stdout.strip(), resultado.codigo_saida) == ("5", 0)


def test_loop_infinito_e_cortado_pelo_tempo() -> None:
    inicio = time.monotonic()

    resultado = executar("while True:\n    pass")

    assert resultado.tempo_esgotado
    # O teto de dentro mais a subida do container, longe do prazo de fora.
    assert time.monotonic() - inicio < settings.sandbox_tempo_segundos + 15


def test_fork_bomb_nao_derruba_nada() -> None:
    codigo = (
        "import os\nwhile True:\n    try:\n        os.fork()\n    except OSError:\n        pass"
    )

    resultado = executar(codigo)

    # Esbarra no `--pids-limit` e morre pelo tempo; o worker segue de pé.
    assert resultado.codigo_saida != 0
    assert executar("print('vivo')").stdout.strip() == "vivo"


def test_nao_le_arquivos_do_sistema() -> None:
    resultado = executar("print(open('/etc/shadow').read())")

    assert resultado.codigo_saida != 0
    assert "PermissionError" in resultado.stderr
    assert "root:" not in resultado.stdout


def test_nao_ve_os_segredos_da_aplicacao() -> None:
    codigo = "import os\nprint(sorted(os.environ))\nprint(os.path.exists('/app'))"

    resultado = executar(codigo)

    assert "JWT_SECRET" not in resultado.stdout
    assert "DATABASE_URL" not in resultado.stdout
    assert resultado.stdout.strip().endswith("False")


def test_disco_e_so_leitura() -> None:
    resultado = executar("open('/home/teste.txt', 'w').write('x')")

    assert resultado.codigo_saida != 0
    assert "Read-only file system" in resultado.stderr or "PermissionError" in resultado.stderr


def test_tmp_nao_executa_binario() -> None:
    codigo = (
        "import os, shutil, subprocess\n"
        "shutil.copy('/bin/busybox', '/tmp/b')\n"
        "os.chmod('/tmp/b', 0o755)\n"
        "subprocess.run(['/tmp/b', 'true'], check=True)"
    )

    resultado = executar(codigo)

    assert resultado.codigo_saida != 0


def test_sem_rede() -> None:
    codigo = (
        "import socket\nsocket.create_connection(('1.1.1.1', 80), timeout=3)\nprint('conectou')"
    )

    resultado = executar(codigo)

    assert "conectou" not in resultado.stdout
    assert resultado.codigo_saida != 0


def test_roda_sem_root_e_sem_capabilities() -> None:
    codigo = (
        "import os\n"
        "print(os.getuid())\n"
        "print([l for l in open('/proc/self/status') if l.startswith('CapEff')][0].split()[1])"
    )

    resultado = executar(codigo)

    uid, capacidades = resultado.stdout.split()
    assert uid == "65534"
    assert int(capacidades, 16) == 0


def test_memoria_tem_teto() -> None:
    resultado = executar("dados = bytearray(1024 * 1024 * 1024)\nprint('alocou')")

    assert "alocou" not in resultado.stdout
    assert resultado.memoria_estourada or "MemoryError" in resultado.stderr


def test_saida_gigante_e_cortada() -> None:
    resultado = executar("while True:\n    print('x' * 1000)")

    assert resultado.saida_cortada
    assert len(resultado.stdout) <= settings.sandbox_saida_maxima


def test_escape_de_terminal_nao_chega_ao_aluno() -> None:
    resultado = executar("print('\\x1b[2J\\x1b[31mlimpou\\x07')")

    assert resultado.stdout.strip() == "limpou"
