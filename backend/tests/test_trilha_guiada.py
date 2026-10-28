"""Revisão dos assuntos, confirmação da ementa e a trilha guiada que sai dela (#38).

Usa o provedor falso de `test_ementa_assuntos`: a leitura vem pronta, e o
embedding por tema decide qual assunto cai em qual módulo.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    Ementa,
    Modulo,
    NivelExperiencia,
    ProgressoUsuario,
    StatusEmenta,
    StatusProgresso,
    Trilha,
    Usuario,
)
from app.services import assuntos_ementa
from tests.test_ementa_assuntos import (
    DISCIPLINA,
    TEXTO_DA_EMENTA,
    ProvedorDeEmenta,
    assuntos,
    enviar,
    situacoes,
)

# Fixtures: o pytest as acha pelo nome no módulo, por isso o import explícito.
from tests.test_ementa_assuntos import midia as midia
from tests.test_ementa_assuntos import provedor as provedor

# Duas disciplinas, a do 2º período primeiro no documento, e dois assuntos que
# caem no mesmo módulo (laços).
LEITURA_GUIADA = {
    "disciplinas": [
        {"nome": "Estruturas de Dados", "periodo": 2, "assuntos": ["Recursão"]},
        {
            "nome": DISCIPLINA,
            "periodo": 1,
            "assuntos": ["Laços de repetição", "Variáveis e tipos", "Repetição com while"],
        },
    ]
}


@pytest.fixture
def python(db: Session) -> Trilha:
    """Quatro passos; o primeiro não cobre nenhum assunto da ementa."""
    trilha = Trilha(slug="python", nome="Python", disciplina=DISCIPLINA, periodo=1, publicada=True)
    trilha.modulos = [
        Modulo(ordem=1, titulo="Iniciando no Python"),
        Modulo(ordem=2, titulo="Variáveis e tipos de dados"),
        Modulo(ordem=3, titulo="Estruturas condicionais"),
        Modulo(ordem=4, titulo="Laços de repetição"),
    ]
    db.add(trilha)
    db.commit()
    return trilha


def com_nivel(db: Session, usuario: Usuario, nivel: NivelExperiencia) -> None:
    usuario = db.merge(usuario)
    usuario.nivel_experiencia = nivel
    db.commit()


def confirmada(cliente: TestClient, autenticado: dict[str, str], provedor: ProvedorDeEmenta) -> int:
    provedor.respostas = [json.dumps(LEITURA_GUIADA)]
    ementa_id = enviar(cliente, autenticado)
    resposta = cliente.post(f"/api/v1/ementas/{ementa_id}/confirmar", headers=autenticado)
    assert resposta.status_code == 200, resposta.text
    return ementa_id


def guiada(cliente: TestClient, autenticado: dict[str, str]) -> dict:
    resposta = cliente.get("/api/v1/trilha-guiada", headers=autenticado)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def resumo(corpo: dict) -> list[tuple]:
    return [
        (item["modulo"]["ordem"], item["base"], item["assuntos"])
        if item["tipo"] == "modulo"
        else ("lacuna", item["status_lacuna"], item["assuntos"])
        for item in corpo["itens"]
    ]


def concluir(db: Session, usuario: Usuario, trilha: Trilha, ordem: int) -> None:
    modulo = next(m for m in trilha.modulos if m.ordem == ordem)
    db.add(
        ProgressoUsuario(
            usuario_id=usuario.id,
            trilha_id=trilha.id,
            modulo_id=modulo.id,
            status=StatusProgresso.concluido,
        )
    )
    db.commit()


# --- ementa atual -------------------------------------------------------------------------


def test_ementa_atual_e_a_ultima_enviada(
    cliente: TestClient, autenticado: dict[str, str], provedor: ProvedorDeEmenta, midia: Path
) -> None:
    sem = cliente.get("/api/v1/ementas/atual", headers=autenticado)
    assert (sem.status_code, sem.json()["erro"]["code"]) == (404, "ementa_nao_encontrada")

    enviar(cliente, autenticado)
    segunda = enviar(cliente, autenticado, [*TEXTO_DA_EMENTA, "Outra turma"])

    atual = cliente.get("/api/v1/ementas/atual", headers=autenticado).json()
    assert (atual["id"], atual["status_assuntos"], atual["confirmada_em"]) == (
        segunda,
        "prontos",
        None,
    )


# --- revisão ------------------------------------------------------------------------------


def test_revisao_remove_renomeia_e_acrescenta_e_so_busca_o_que_mudou(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorDeEmenta,
    python: Trilha,
    midia: Path,
) -> None:
    ementa_id = enviar(cliente, autenticado)
    provedor.embedados.clear()

    revisao = {
        "disciplinas": [
            {
                "nome": DISCIPLINA,
                "periodo": 1,
                # "Estruturas condicionais" e "Recursão" saem; "Laços" muda de
                # caixa, e não conta como novo; "Condicionais aninhadas" entra.
                "assuntos": ["Variáveis e tipos", "LAÇOS DE REPETIÇÃO", "Condicionais aninhadas"],
            }
        ]
    }
    resposta = cliente.put(
        f"/api/v1/ementas/{ementa_id}/assuntos", headers=autenticado, json=revisao
    )

    assert resposta.status_code == 200, resposta.text
    assert situacoes(resposta.json()) == {
        "Variáveis e tipos": "coberto",
        "LAÇOS DE REPETIÇÃO": "coberto",
        "Condicionais aninhadas": "coberto",
    }
    assert provedor.embedados == [f"{DISCIPLINA}: Condicionais aninhadas"]
    assert assuntos(cliente, autenticado, ementa_id) == resposta.json()


def test_revisao_junta_disciplina_repetida_e_assunto_duplicado(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorDeEmenta,
    python: Trilha,
    midia: Path,
) -> None:
    ementa_id = enviar(cliente, autenticado)
    revisao = {
        "disciplinas": [
            {"nome": DISCIPLINA, "assuntos": ["Variáveis e tipos", "variaveis e tipos"]},
            {"nome": DISCIPLINA.upper(), "assuntos": ["Recursão"]},
        ]
    }

    corpo = cliente.put(
        f"/api/v1/ementas/{ementa_id}/assuntos", headers=autenticado, json=revisao
    ).json()

    [disciplina] = corpo["disciplinas"]
    assert [a["texto"] for a in disciplina["assuntos"]] == ["Variáveis e tipos", "Recursão"]


def test_revisao_com_ia_fora_nao_muda_nada(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorDeEmenta,
    python: Trilha,
    midia: Path,
) -> None:
    ementa_id = enviar(cliente, autenticado)
    antes = assuntos(cliente, autenticado, ementa_id)
    provedor.embeddings_fora = True

    resposta = cliente.put(
        f"/api/v1/ementas/{ementa_id}/assuntos",
        headers=autenticado,
        json={"disciplinas": [{"nome": DISCIPLINA, "assuntos": ["Ponteiros"]}]},
    )

    assert resposta.status_code == 503
    assert resposta.json()["erro"]["code"] == "ia_indisponivel"
    assert assuntos(cliente, autenticado, ementa_id) == antes


def test_revisao_so_remove_sem_chamar_a_ia(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorDeEmenta,
    python: Trilha,
    midia: Path,
) -> None:
    ementa_id = enviar(cliente, autenticado)
    provedor.embeddings_fora = True

    resposta = cliente.put(
        f"/api/v1/ementas/{ementa_id}/assuntos",
        headers=autenticado,
        json={"disciplinas": [{"nome": DISCIPLINA, "assuntos": ["Recursão"]}]},
    )

    assert resposta.status_code == 200, resposta.text
    assert situacoes(resposta.json()) == {"Recursão": "lacuna"}


@pytest.mark.parametrize(
    "corpo",
    [
        {"disciplinas": []},
        {"disciplinas": [{"nome": DISCIPLINA, "assuntos": []}]},
        {"disciplinas": [{"nome": " ", "assuntos": ["Laços"]}]},
        {"disciplinas": [{"nome": DISCIPLINA, "assuntos": ["x" * 301]}]},
    ],
)
def test_revisao_invalida_e_recusada(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorDeEmenta,
    python: Trilha,
    midia: Path,
    corpo: dict,
) -> None:
    ementa_id = enviar(cliente, autenticado)

    resposta = cliente.put(f"/api/v1/ementas/{ementa_id}/assuntos", headers=autenticado, json=corpo)

    assert resposta.status_code == 422


def test_revisao_e_confirmacao_antes_dos_assuntos_respondem_409(
    cliente: TestClient, autenticado: dict[str, str], usuario: Usuario, db: Session
) -> None:
    ementa = Ementa(usuario_id=usuario.id, arquivo_path="x.pdf", status=StatusEmenta.processada)
    db.add(ementa)
    db.commit()

    revisao = cliente.put(
        f"/api/v1/ementas/{ementa.id}/assuntos",
        headers=autenticado,
        json={"disciplinas": [{"nome": DISCIPLINA, "assuntos": ["Laços"]}]},
    )
    confirmacao = cliente.post(f"/api/v1/ementas/{ementa.id}/confirmar", headers=autenticado)

    assert (revisao.status_code, confirmacao.status_code) == (409, 409)
    assert confirmacao.json()["erro"]["code"] == "assuntos_indisponiveis"


# --- trilha guiada ------------------------------------------------------------------------


def test_sem_ementa_confirmada_nao_ha_trilha_guiada(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorDeEmenta,
    python: Trilha,
    midia: Path,
) -> None:
    enviar(cliente, autenticado)

    resposta = cliente.get("/api/v1/trilha-guiada", headers=autenticado)

    assert resposta.status_code == 404
    assert resposta.json()["erro"]["code"] == "trilha_guiada_inexistente"


def test_trilha_guiada_segue_o_periodo_e_junta_assuntos_do_mesmo_modulo(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorDeEmenta,
    python: Trilha,
    midia: Path,
    db: Session,
    usuario: Usuario,
) -> None:
    com_nivel(db, usuario, NivelExperiencia.medio)
    ementa_id = confirmada(cliente, autenticado, provedor)

    corpo = guiada(cliente, autenticado)

    assert (corpo["ementa_id"], corpo["nivel"], corpo["total_modulos"]) == (ementa_id, "medio", 2)
    assert resumo(corpo) == [
        (4, False, ["Laços de repetição", "Repetição com while"]),
        (2, False, ["Variáveis e tipos"]),
        ("lacuna", "pendente", ["Recursão"]),
    ]
    assert [item["disciplina"] for item in corpo["itens"]] == [
        DISCIPLINA,
        DISCIPLINA,
        "Estruturas de Dados",
    ]


def test_nivel_baixo_comeca_pelos_modulos_anteriores_da_trilha(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorDeEmenta,
    python: Trilha,
    midia: Path,
    db: Session,
    usuario: Usuario,
) -> None:
    com_nivel(db, usuario, NivelExperiencia.baixo)
    confirmada(cliente, autenticado, provedor)

    # O módulo 2 entrou como base do 4, mas a ementa também pede o assunto dele.
    assert resumo(guiada(cliente, autenticado)) == [
        (1, True, []),
        (2, False, ["Variáveis e tipos"]),
        (3, True, []),
        (4, False, ["Laços de repetição", "Repetição com while"]),
        ("lacuna", "pendente", ["Recursão"]),
    ]


def test_revisao_depois_de_confirmar_muda_a_trilha_guiada(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorDeEmenta,
    python: Trilha,
    midia: Path,
    db: Session,
    usuario: Usuario,
) -> None:
    com_nivel(db, usuario, NivelExperiencia.alto)
    ementa_id = confirmada(cliente, autenticado, provedor)

    cliente.put(
        f"/api/v1/ementas/{ementa_id}/assuntos",
        headers=autenticado,
        json={"disciplinas": [{"nome": DISCIPLINA, "assuntos": ["Estruturas condicionais"]}]},
    )

    assert resumo(guiada(cliente, autenticado)) == [(3, False, ["Estruturas condicionais"])]


# --- desbloqueio --------------------------------------------------------------------------


def test_trilha_guiada_libera_o_passo_que_o_catalogo_ainda_trancaria(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorDeEmenta,
    python: Trilha,
    midia: Path,
    db: Session,
    usuario: Usuario,
) -> None:
    """Nível médio: a trilha guiada começa no passo 4 do catálogo, sem o 1, o 2 e o 3."""
    com_nivel(db, usuario, NivelExperiencia.medio)
    confirmada(cliente, autenticado, provedor)

    def status_do_passo(ordem: int) -> int:
        return cliente.get(
            f"/api/v1/trilhas/python/passos/{ordem}", headers=autenticado
        ).status_code

    estados = [i["modulo"]["status"] for i in guiada(cliente, autenticado)["itens"] if i["modulo"]]
    assert estados == ["em-andamento", "bloqueado"]
    assert (status_do_passo(4), status_do_passo(2), status_do_passo(3)) == (200, 403, 403)

    concluir(db, usuario, python, 4)

    corpo = guiada(cliente, autenticado)
    estados = [i["modulo"]["status"] for i in corpo["itens"] if i["modulo"]]
    assert (estados, corpo["concluidos"]) == (["concluido", "em-andamento"], 1)
    # O 2 abriu pela trilha guiada; o 3 continua esperando o 2, pela ordem do catálogo.
    assert (status_do_passo(2), status_do_passo(3)) == (200, 403)


def test_sem_trilha_guiada_o_catalogo_segue_a_ordem_de_sempre(
    cliente: TestClient, autenticado: dict[str, str], python: Trilha
) -> None:
    def status_do_passo(ordem: int) -> int:
        return cliente.get(
            f"/api/v1/trilhas/python/passos/{ordem}", headers=autenticado
        ).status_code

    assert (status_do_passo(1), status_do_passo(2)) == (200, 403)


def test_confirmar_de_novo_faz_da_ementa_a_base(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorDeEmenta,
    python: Trilha,
    midia: Path,
    db: Session,
) -> None:
    primeira = confirmada(cliente, autenticado, provedor)
    segunda = confirmada(cliente, autenticado, provedor)
    assert guiada(cliente, autenticado)["ementa_id"] == segunda

    cliente.post(f"/api/v1/ementas/{primeira}/confirmar", headers=autenticado)

    assert guiada(cliente, autenticado)["ementa_id"] == primeira
    assert assuntos_ementa.confirmar(db, db.get(Ementa, primeira))
