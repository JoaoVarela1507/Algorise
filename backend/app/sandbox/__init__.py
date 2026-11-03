"""Execução isolada do código do aluno (#34).

É a superfície de risco mais alta do projeto: o código vem de qualquer um e roda
no nosso servidor. Cada execução é um container novo, descartado no fim, com:

| Contenção                  | Como                                                        |
| -------------------------- | ----------------------------------------------------------- |
| sem rede                   | `--network none`                                            |
| disco só de leitura        | `--read-only`, com um `/tmp` pequeno, `noexec`, na memória  |
| sem root                   | `--user` nobody, `--cap-drop ALL`, `no-new-privileges`      |
| memória                    | `--memory` igual a `--memory-swap`: sem swap para fugir      |
| CPU                        | `--cpus`                                                    |
| fork bomb                  | `--pids-limit`                                              |
| tempo                      | `timeout -s KILL` dentro do container, e `docker kill` fora |
| tamanho da saída           | a leitura para no teto e o container é morto                |
| arquivos grandes           | `--ulimit fsize`                                            |

O Python roda com `-I` (sem variáveis de ambiente nem diretório do usuário no
path) e sem gravar bytecode. A imagem é a oficial `python:*-alpine`, sem nada
nosso dentro: não há segredo para ler.

Fica de fora o kernel: o container divide o do host. Em produção, use o gVisor
(`SANDBOX_RUNTIME=runsc`), que põe um kernel de mentira no meio. E o worker
precisa falar com o Docker: veja o README sobre o socket.
"""

import re
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass
from typing import IO

from app.core.config import settings


class SandboxIndisponivel(Exception):
    """Sem Docker, ou a sandbox desligada por configuração."""


@dataclass(frozen=True)
class Resultado:
    stdout: str
    stderr: str
    codigo_saida: int
    tempo_esgotado: bool = False
    memoria_estourada: bool = False
    saida_cortada: bool = False


DOCKER = "docker"
# Códigos que o `timeout -s KILL` e o kernel devolvem quando matam o processo.
_MORTO = {124, 137}
_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b[@-_]")
_CONTROLE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def sanitizar(bruto: bytes, limite: int) -> str:
    """Texto seguro para devolver: UTF-8 válido, sem escapes de terminal, com teto."""
    texto = bruto[:limite].decode("utf-8", errors="replace")
    texto = _ANSI.sub("", texto.replace("\r\n", "\n"))
    return _CONTROLE.sub("", texto)


def comando(nome: str, codigo: str) -> list[str]:
    """A linha do `docker run`, separada para o teste conferir cada contenção."""
    linha = [
        DOCKER,
        "run",
        "--name",
        nome,
        "--interactive",
        "--network",
        "none",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=8m",
        "--user",
        "65534:65534",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--memory",
        f"{settings.sandbox_memoria_mb}m",
        "--memory-swap",
        f"{settings.sandbox_memoria_mb}m",
        "--cpus",
        str(settings.sandbox_cpus),
        "--pids-limit",
        str(settings.sandbox_processos),
        "--ulimit",
        "fsize=1048576",
        "--ulimit",
        "nofile=64:64",
        "--env",
        "PYTHONDONTWRITEBYTECODE=1",
        "--workdir",
        "/tmp",
    ]
    if settings.sandbox_runtime:
        linha += ["--runtime", settings.sandbox_runtime]
    linha += [
        settings.sandbox_imagem,
        "timeout",
        "-s",
        "KILL",
        str(settings.sandbox_tempo_segundos),
        "python",
        "-I",
        "-c",
        codigo,
    ]
    return linha


def executar(codigo: str, entrada: str = "") -> Resultado:
    """Roda `codigo` com `entrada` no stdin, num container descartável."""
    if settings.sandbox_modo != "docker":
        raise SandboxIndisponivel("A sandbox está desligada (SANDBOX_MODO)")
    nome = f"algorise-exec-{uuid.uuid4().hex[:16]}"
    limite = settings.sandbox_saida_maxima
    try:
        processo = subprocess.Popen(
            comando(nome, codigo),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as erro:
        raise SandboxIndisponivel("O Docker não está instalado") from erro

    saidas: dict[str, bytes] = {}
    cortada = threading.Event()

    def ler(nome_do_fluxo: str, fluxo: IO[bytes]) -> None:
        lido = bytearray()
        while chunk := fluxo.read(4096):
            lido += chunk
            if len(lido) > limite:
                # Passou do teto: para de ler e mata o container, senão um
                # `while True: print()` enche a memória do worker.
                cortada.set()
                _matar(nome)
                break
        saidas[nome_do_fluxo] = bytes(lido)

    leitores = [
        threading.Thread(target=ler, args=("stdout", processo.stdout), daemon=True),
        threading.Thread(target=ler, args=("stderr", processo.stderr), daemon=True),
    ]
    for leitor in leitores:
        leitor.start()

    # O tempo de fora cobre o de dentro mais a subida do container.
    prazo = settings.sandbox_tempo_segundos + 20
    inicio = time.monotonic()
    try:
        if processo.stdin is not None:
            try:
                processo.stdin.write(entrada.encode("utf-8"))
                processo.stdin.close()
            except BrokenPipeError:
                pass
        processo.wait(timeout=prazo)
    except subprocess.TimeoutExpired:
        _matar(nome)
        processo.wait(timeout=10)
    finally:
        for leitor in leitores:
            leitor.join(timeout=5)
        memoria = _morto_por_memoria(nome)
        _remover(nome)

    codigo_saida = processo.returncode
    if codigo_saida == 125:
        # 125 é o próprio Docker falhando (imagem ausente, daemon fora).
        raise SandboxIndisponivel(sanitizar(saidas.get("stderr", b""), 2000))
    demorou = time.monotonic() - inicio >= prazo
    return Resultado(
        stdout=sanitizar(saidas.get("stdout", b""), limite),
        stderr=sanitizar(saidas.get("stderr", b""), limite),
        codigo_saida=codigo_saida,
        tempo_esgotado=demorou or (codigo_saida in _MORTO and not memoria and not cortada.is_set()),
        memoria_estourada=memoria,
        saida_cortada=cortada.is_set(),
    )


def _matar(nome: str) -> None:
    subprocess.run([DOCKER, "kill", nome], capture_output=True, timeout=15, check=False)


def _morto_por_memoria(nome: str) -> bool:
    resposta = subprocess.run(
        [DOCKER, "inspect", "--format", "{{.State.OOMKilled}}", nome],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    return resposta.stdout.strip() == "true"


def _remover(nome: str) -> None:
    subprocess.run([DOCKER, "rm", "--force", nome], capture_output=True, timeout=30, check=False)
