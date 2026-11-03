"""Desafio de código (#34): a API, a correção pelos casos e o XP.

A sandbox de verdade (Docker) tem os testes de contenção dela em
`test_sandbox_contencao.py`. Aqui ela é trocada por uma falsa, que responde
pelo código: o que se testa é o caminho até ela e o que se faz com a resposta.
"""

from collections.abc import Iterator

import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    Atividade,
    CasoDeTeste,
    Execucao,
    Modulo,
    OrigemXP,
    StatusExecucao,
    TipoAtividade,
    Trilha,
    Usuario,
    XPEvento,
)
from app.sandbox import Resultado, SandboxIndisponivel, comando, sanitizar
from app.services import desafios

URL = "/api/v1"


@pytest.fixture
def desafio(db: Session) -> Atividade:
    trilha = Trilha(slug="py", nome="Python", disciplina="Algoritmos", publicada=True)
    trilha.modulos = [Modulo(ordem=1, titulo="Projeto")]
    atividade = Atividade(
        ordem=1, tipo=TipoAtividade.desafio_codigo, enunciado="Some", dica="Use sum", xp=40
    )
    trilha.modulos[0].atividades = [atividade]
    db.add(trilha)
    db.commit()
    db.add_all(
        [
            CasoDeTeste(atividade_id=atividade.id, ordem=1, entrada="1 2", saida_esperada="3"),
            CasoDeTeste(
                atividade_id=atividade.id,
                ordem=2,
                entrada="5 5",
                saida_esperada="10",
                publico=False,
            ),
        ]
    )
    db.commit()
    return atividade


@pytest.fixture
def sandbox(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[tuple[str, str]]]:
    """Sandbox falsa: soma os números da entrada se o código pede `sum`."""
    chamadas: list[tuple[str, str]] = []

    def rodar(codigo: str, entrada: str = "") -> Resultado:
        chamadas.append((codigo, entrada))
        if "indisponivel" in codigo:
            raise SandboxIndisponivel("sem Docker")
        if "while True" in codigo:
            return Resultado(stdout="", stderr="", codigo_saida=137, tempo_esgotado=True)
        if "raise" in codigo:
            return Resultado(stdout="", stderr="Traceback: ValueError", codigo_saida=1)
        if "sum" in codigo:
            total = sum(int(n) for n in entrada.split())
            return Resultado(stdout=f"{total}\n", stderr="", codigo_saida=0)
        return Resultado(stdout="errado\n", stderr="", codigo_saida=0)

    monkeypatch.setattr(desafios, "rodar_na_sandbox", rodar)
    yield chamadas


def executar(cliente: TestClient, headers: dict[str, str], desafio: Atividade, codigo: str) -> dict:
    resposta = cliente.post(
        f"{URL}/desafios/{desafio.id}/execucoes", json={"codigo": codigo}, headers=headers
    )
    assert resposta.status_code == 202, resposta.text
    # No modo `local`, a fila roda depois da resposta, ainda dentro do TestClient.
    return cliente.get(f"{URL}/execucoes/{resposta.json()['id']}", headers=headers).json()


# --- enunciado ----------------------------------------------------------------------------


def test_desafio_mostra_so_os_casos_publicos(cliente: TestClient, desafio: Atividade) -> None:
    corpo = cliente.get(f"{URL}/desafios/{desafio.id}").json()

    assert corpo["enunciado"] == "Some"
    assert corpo["casos_publicos"] == [{"ordem": 1, "entrada": "1 2", "saida_esperada": "3"}]
    assert corpo["total_casos"] == 2


def test_atividade_que_nao_e_desafio_da_404(cliente: TestClient, db: Session) -> None:
    trilha = Trilha(slug="t", nome="T", disciplina="D", publicada=True)
    trilha.modulos = [Modulo(ordem=1, titulo="M")]
    trilha.modulos[0].atividades = [
        Atividade(ordem=1, tipo=TipoAtividade.terminal, enunciado="e", comando_esperado="ls")
    ]
    db.add(trilha)
    db.commit()

    resposta = cliente.get(f"{URL}/desafios/{trilha.modulos[0].atividades[0].id}")

    assert resposta.status_code == 404
    assert resposta.json()["erro"]["code"] == "desafio_nao_encontrado"


# --- execução -----------------------------------------------------------------------------


def test_codigo_certo_passa_em_todos_e_paga_o_xp_uma_vez(
    cliente: TestClient,
    autenticado: dict[str, str],
    desafio: Atividade,
    sandbox: list,
    db: Session,
    usuario: Usuario,
) -> None:
    primeira = executar(cliente, autenticado, desafio, "print(sum(map(int, input().split())))")
    segunda = executar(cliente, autenticado, desafio, "print(sum(map(int, input().split())))")

    assert (primeira["status"], primeira["aprovada"]) == ("concluida", True)
    assert [c["passou"] for c in primeira["casos"]] == [True, True]
    assert len(sandbox) == 4  # um container por caso, nas duas execuções
    assert segunda["aprovada"] is True
    xp = db.scalars(
        select(XPEvento).where(
            XPEvento.usuario_id == usuario.id, XPEvento.origem == OrigemXP.atividade
        )
    ).all()
    assert [e.valor for e in xp] == [40]


def test_caso_publico_mostra_o_que_saiu_e_o_oculto_nao(
    cliente: TestClient, autenticado: dict[str, str], desafio: Atividade, sandbox: list
) -> None:
    corpo = executar(cliente, autenticado, desafio, "print('errado')")

    assert corpo["aprovada"] is False
    [caso] = corpo["casos"]  # parou no primeiro que falhou
    assert caso == {
        "ordem": 1,
        "publico": True,
        "passou": False,
        "motivo": "saida_diferente",
        "entrada": "1 2",
        "esperado": "3",
        "obtido": "errado\n",
    }


def test_caso_oculto_que_falha_nao_revela_a_entrada(
    cliente: TestClient,
    autenticado: dict[str, str],
    desafio: Atividade,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Acerta o público (1 2 -> 3) e erra o oculto.
    monkeypatch.setattr(
        desafios,
        "rodar_na_sandbox",
        lambda codigo, entrada="": Resultado(stdout="3", stderr="", codigo_saida=0),
    )

    corpo = executar(cliente, autenticado, desafio, "print(3)")

    oculto = corpo["casos"][1]
    assert oculto["passou"] is False
    assert oculto["entrada"] is None and oculto["esperado"] is None and oculto["obtido"] is None


@pytest.mark.parametrize(
    ("codigo", "motivo"),
    [("while True: pass", "tempo_esgotado"), ("raise ValueError", "erro_de_execucao")],
)
def test_motivo_da_falha(
    cliente: TestClient,
    autenticado: dict[str, str],
    desafio: Atividade,
    sandbox: list,
    codigo: str,
    motivo: str,
) -> None:
    corpo = executar(cliente, autenticado, desafio, codigo)

    assert corpo["casos"][0]["motivo"] == motivo
    assert corpo["aprovada"] is False


def test_sandbox_fora_marca_a_execucao_como_falhou(
    cliente: TestClient, autenticado: dict[str, str], desafio: Atividade, sandbox: list
) -> None:
    corpo = executar(cliente, autenticado, desafio, "indisponivel")

    assert corpo["status"] == "falhou"
    assert corpo["erro"] == "A correção está fora do ar agora."


def test_desafio_sem_casos_nunca_e_aprovado(
    cliente: TestClient,
    autenticado: dict[str, str],
    desafio: Atividade,
    sandbox: list,
    db: Session,
) -> None:
    for caso in db.scalars(select(CasoDeTeste)).all():
        db.delete(caso)
    db.commit()

    corpo = executar(cliente, autenticado, desafio, "print(sum([]))")

    assert (corpo["status"], corpo["aprovada"]) == ("concluida", False)


def test_execucao_de_outro_aluno_e_404(
    cliente: TestClient, autenticado: dict[str, str], desafio: Atividade, db: Session
) -> None:
    dona = Usuario(email="bia@ufrpe.br", username="bia", nome_exibicao="Bia")
    db.add(dona)
    db.commit()
    alheia = desafios.criar_execucao(db, dona, desafio, "print(1)")

    resposta = cliente.get(f"{URL}/execucoes/{alheia.id}", headers=autenticado)

    assert resposta.status_code == 404


def test_codigo_grande_demais_e_recusado(
    cliente: TestClient, autenticado: dict[str, str], desafio: Atividade
) -> None:
    resposta = cliente.post(
        f"{URL}/desafios/{desafio.id}/execucoes",
        json={"codigo": "x" * (settings.sandbox_codigo_maximo + 1)},
        headers=autenticado,
    )

    assert resposta.status_code == 422


def test_rate_limit_por_aluno(
    cliente: TestClient,
    autenticado: dict[str, str],
    desafio: Atividade,
    sandbox: list,
    redis_falso: fakeredis.FakeRedis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "rate_limit_execucoes_requisicoes", 2)
    url = f"{URL}/desafios/{desafio.id}/execucoes"

    codigos = [
        cliente.post(url, json={"codigo": "print(1)"}, headers=autenticado).status_code
        for _ in range(3)
    ]

    assert codigos == [202, 202, 429]


def test_execucao_presa_vira_falhou(db: Session, desafio: Atividade, usuario: Usuario) -> None:
    execucao = desafios.criar_execucao(db, usuario, desafio, "print(1)")

    desafios.falhar(db, execucao.id, "A execução não terminou a tempo.")

    db.refresh(execucao)
    assert execucao.status is StatusExecucao.falhou


def test_execucao_ja_rodada_nao_roda_de_novo(
    db: Session, desafio: Atividade, usuario: Usuario, sandbox: list
) -> None:
    execucao = desafios.criar_execucao(db, usuario, desafio, "print(sum([1]))")
    desafios.executar(db, execucao.id)
    desafios.executar(db, execucao.id)

    assert len(sandbox) == 2
    assert db.get(Execucao, execucao.id).status is StatusExecucao.concluida


# --- regras puras -------------------------------------------------------------------------


def test_saida_e_conferida_sem_espaco_no_fim() -> None:
    assert desafios.normalizar_saida("3  \r\n\n\n") == "3"
    assert desafios.normalizar_saida("a \nb\n") == "a\nb"


def test_sanitizar_tira_escape_de_terminal_e_corta() -> None:
    bruto = b"\x1b[31mvermelho\x1b[0m\x07 ok\xff\n" + b"x" * 100

    texto = sanitizar(bruto, 30)

    assert texto.startswith("vermelho ok�\n")
    assert "\x1b" not in texto and "\x07" not in texto
    assert len(texto) <= 30


def test_comando_liga_todas_as_contencoes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "sandbox_runtime", "runsc")

    linha = comando("nome", "print(1)")
    texto = " ".join(linha)

    for trecho in (
        "--network none",
        "--read-only",
        "--user 65534:65534",
        "--cap-drop ALL",
        "--security-opt no-new-privileges",
        f"--memory {settings.sandbox_memoria_mb}m",
        f"--memory-swap {settings.sandbox_memoria_mb}m",
        f"--pids-limit {settings.sandbox_processos}",
        "--runtime runsc",
        f"timeout -s KILL {settings.sandbox_tempo_segundos} python -I -c",
    ):
        assert trecho in texto, trecho
    # O código vai como um argumento só, sem passar por shell.
    assert linha[-1] == "print(1)"


def test_sandbox_desligada_recusa(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import sandbox as modulo

    monkeypatch.setattr(settings, "sandbox_modo", "desligada")

    with pytest.raises(SandboxIndisponivel):
        modulo.executar("print(1)")
