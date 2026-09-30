"""Testes do contrato fixado na #26: prefixo, formato de erro, paginação e rastreio.

Contrato é o tipo de coisa que quebra sem ninguém perceber — a rota continua
respondendo 200, só que com outra forma. Estes testes falham quando isso
acontece.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.rastreio import CABECALHO_ID, CABECALHO_TEMPO
from app.main import app
from app.models import Trilha


@pytest.fixture
def catalogo(db: Session) -> list[Trilha]:
    """Sete trilhas publicadas e uma em rascunho."""
    trilhas = [
        Trilha(
            slug=f"trilha-{i}",
            nome=f"Trilha {i:02d}",
            disciplina="Algoritmos" if i % 2 else "Estruturas",
            periodo=(i % 4) + 1,
            publicada=True,
        )
        for i in range(1, 8)
    ]
    trilhas.append(
        Trilha(slug="rascunho", nome="Rascunho", disciplina="X", periodo=1, publicada=False)
    )
    db.add_all(trilhas)
    db.commit()
    return trilhas


# --------------------------------------------------------------------------
# Prefixo
# --------------------------------------------------------------------------


def test_rota_de_negocio_vive_sob_o_prefixo(cliente: TestClient) -> None:
    assert cliente.get("/api/v1/trilhas").status_code == 200
    assert cliente.get("/trilhas").status_code == 404


@pytest.mark.parametrize("rota", ["/health", "/ready", "/version"])
def test_rota_de_operacao_fica_fora_do_prefixo(cliente: TestClient, rota: str) -> None:
    """O healthcheck do container não pode mudar de endereço quando a API virar v2."""
    assert cliente.get(rota).status_code in (200, 503)
    assert cliente.get(f"/api/v1{rota}").status_code == 404


# --------------------------------------------------------------------------
# Formato de erro
# --------------------------------------------------------------------------


def test_404_usa_o_formato_unico(cliente: TestClient) -> None:
    resposta = cliente.get("/api/v1/trilhas/nao-existe")

    assert resposta.status_code == 404
    corpo = resposta.json()
    assert set(corpo) == {"erro"}
    assert corpo["erro"]["code"] == "trilha_nao_encontrada"
    assert corpo["erro"]["details"]["slug"] == "nao-existe"
    assert corpo["erro"]["request_id"]


def test_422_de_validacao_usa_o_formato_unico(cliente: TestClient) -> None:
    """O 422 do Pydantic sai numa lista com `loc`/`msg`/`type`; aqui ele é achatado."""
    resposta = cliente.post("/api/v1/auth/login", json={"email": "nao-e-email", "senha": "x"})

    corpo = resposta.json()
    assert resposta.status_code == 422
    assert corpo["erro"]["code"] == "dados_invalidos"
    assert corpo["erro"]["details"]["campos"][0]["campo"] == "email"
    assert corpo["erro"]["message"].startswith("email:")


def test_401_usa_o_formato_unico(cliente: TestClient) -> None:
    resposta = cliente.get("/api/v1/auth/eu")

    assert resposta.json()["erro"]["code"] == "nao_autenticado"


def test_500_nao_vaza_a_excecao(cliente: TestClient) -> None:
    """Stack trace costuma levar junto caminho de arquivo, SQL e dado de usuário."""

    @app.get("/api/v1/_rota_que_explode")
    def _explodir() -> None:
        raise RuntimeError("segredo: senha=123 em /var/lib/postgres")

    try:
        resposta = cliente.get("/api/v1/_rota_que_explode")

        assert resposta.status_code == 500
        assert resposta.json()["erro"]["code"] == "erro_interno"
        assert "senha=123" not in resposta.text
        assert "RuntimeError" not in resposta.text
        assert resposta.json()["erro"]["request_id"]
    finally:
        _remover_rota(app, "/api/v1/_rota_que_explode")


def _remover_rota(aplicacao: FastAPI, caminho: str) -> None:
    """A rota é registrada dentro do teste; sem isso ela vazaria para os outros."""
    aplicacao.router.routes = [
        rota for rota in aplicacao.router.routes if getattr(rota, "path", None) != caminho
    ]


# --------------------------------------------------------------------------
# Paginação
# --------------------------------------------------------------------------


def test_pagina_tem_a_forma_combinada(cliente: TestClient, catalogo: list[Trilha]) -> None:
    corpo = cliente.get("/api/v1/trilhas", params={"tamanho_pagina": 3}).json()

    assert set(corpo) == {"itens", "pagina", "tamanho_pagina", "total", "total_paginas"}
    assert len(corpo["itens"]) == 3
    assert corpo["total"] == 7, "o total conta tudo, não só a página"
    assert corpo["total_paginas"] == 3, "7 em páginas de 3 dá 3 páginas"


def test_paginas_nao_repetem_itens(cliente: TestClient, catalogo: list[Trilha]) -> None:
    def slugs(pagina: int) -> set[str]:
        corpo = cliente.get(
            "/api/v1/trilhas", params={"tamanho_pagina": 3, "pagina": pagina}
        ).json()
        return {item["slug"] for item in corpo["itens"]}

    assert slugs(1).isdisjoint(slugs(2))
    assert len(slugs(3)) == 1, "a última página traz o resto"


def test_pagina_alem_do_fim_vem_vazia(cliente: TestClient, catalogo: list[Trilha]) -> None:
    """Vazia, e não 404: a lista existe, o aluno só passou do fim."""
    corpo = cliente.get("/api/v1/trilhas", params={"pagina": 99}).json()

    assert corpo["itens"] == []
    assert corpo["total"] == 7


def test_trilha_nao_publicada_fica_de_fora(cliente: TestClient, catalogo: list[Trilha]) -> None:
    corpo = cliente.get("/api/v1/trilhas").json()

    assert all(item["slug"] != "rascunho" for item in corpo["itens"])
    assert corpo["total"] == 7


def test_ordenacao_por_campo_permitido(cliente: TestClient, catalogo: list[Trilha]) -> None:
    subindo = cliente.get("/api/v1/trilhas", params={"ordenar_por": "nome"}).json()["itens"]
    descendo = cliente.get(
        "/api/v1/trilhas", params={"ordenar_por": "nome", "decrescente": True}
    ).json()["itens"]

    nomes = [item["nome"] for item in subindo]
    assert nomes == sorted(nomes)
    assert [item["nome"] for item in descendo] == sorted(nomes, reverse=True)


def test_ordenar_por_campo_proibido_e_recusado(cliente: TestClient) -> None:
    """`ordenar_por` vira nome de coluna: sem a lista, o cliente escolheria qualquer uma."""
    resposta = cliente.get("/api/v1/trilhas", params={"ordenar_por": "senha_hash"})

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["code"] == "ordenacao_invalida"
    assert "periodo" in resposta.json()["erro"]["details"]["permitidos"]


@pytest.mark.parametrize(
    "parametros",
    [{"tamanho_pagina": 5000}, {"tamanho_pagina": 0}, {"pagina": 0}],
    ids=["pagina grande demais", "pagina de tamanho zero", "pagina zero"],
)
def test_limites_da_paginacao(cliente: TestClient, parametros: dict[str, int]) -> None:
    assert cliente.get("/api/v1/trilhas", params=parametros).status_code == 422


def test_filtro_por_periodo(cliente: TestClient, catalogo: list[Trilha]) -> None:
    corpo = cliente.get("/api/v1/trilhas", params={"periodo": 2}).json()

    assert corpo["itens"], "o catálogo do teste tem trilha no período 2"
    assert all(item["periodo"] == 2 for item in corpo["itens"])
    assert corpo["total"] == len(corpo["itens"])


# --------------------------------------------------------------------------
# Rastreio
# --------------------------------------------------------------------------


def test_resposta_traz_id_e_tempo(cliente: TestClient) -> None:
    resposta = cliente.get("/api/v1/trilhas")

    assert resposta.headers[CABECALHO_ID]
    assert resposta.headers[CABECALHO_TEMPO].isdigit()


def test_cada_requisicao_tem_id_proprio(cliente: TestClient) -> None:
    primeira = cliente.get("/api/v1/trilhas").headers[CABECALHO_ID]
    segunda = cliente.get("/api/v1/trilhas").headers[CABECALHO_ID]

    assert primeira != segunda


def test_id_vindo_do_proxy_e_reaproveitado(cliente: TestClient) -> None:
    resposta = cliente.get("/api/v1/trilhas", headers={CABECALHO_ID: "trace-do-proxy-1"})

    assert resposta.headers[CABECALHO_ID] == "trace-do-proxy-1"


def test_id_vindo_de_fora_e_sanado(cliente: TestClient) -> None:
    """Ele vai para o log: não pode levar quebra de linha nem 8 KB de lixo."""
    sujo = cliente.get("/api/v1/trilhas", headers={CABECALHO_ID: "abc\tdef ghi;rm -rf"})
    longo = cliente.get("/api/v1/trilhas", headers={CABECALHO_ID: "a" * 500})

    assert sujo.headers[CABECALHO_ID] == "abcdefghirm-rf"
    assert len(longo.headers[CABECALHO_ID]) == 64


def test_id_do_header_aparece_no_corpo_do_erro(cliente: TestClient) -> None:
    resposta = cliente.get("/api/v1/trilhas/nao-existe", headers={CABECALHO_ID: "meu-id-9"})

    assert resposta.json()["erro"]["request_id"] == "meu-id-9"


# --------------------------------------------------------------------------
# OpenAPI
# --------------------------------------------------------------------------


def test_operation_id_e_unico_e_legivel() -> None:
    """Ele vira nome de função no cliente TypeScript gerado (`npm run gen:api`)."""
    esquema = app.openapi()
    ids = [
        operacao["operationId"]
        for caminho in esquema["paths"].values()
        for operacao in caminho.values()
    ]

    assert all(ids), "toda rota precisa de operationId"
    assert len(ids) == len(set(ids)), "id repetido quebra o cliente gerado"
    assert "listarTrilhas" in ids
    assert not any("api_v1" in identificador for identificador in ids), (
        "o id não pode carregar a rota dentro: mover a rota renomearia o cliente"
    )


def test_formato_de_erro_esta_documentado() -> None:
    esquema = app.openapi()

    assert "RespostaDeErro" in esquema["components"]["schemas"]
    assert "422" in esquema["paths"]["/api/v1/trilhas"]["get"]["responses"]
