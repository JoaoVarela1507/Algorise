"""Testes do onboarding acadêmico (#28): catálogo, `POST /onboarding` e ementa em PDF.

Duas coisas pesam mais aqui. A busca precisa achar a instituição do jeito que o
aluno digita — sem acento, pela sigla, com erro —, e não pode transformar o que
um aluno digitou em sugestão para os outros. E a ementa é arquivo do aluno: não
tem URL pública, e a de um não aparece para outro.
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Curso, Ementa, Instituicao, StatusEmenta, Trilha, Usuario
from app.seeds import academico
from app.services import auth as servico_auth
from app.services import catalogo, conta
from tests.conftest import SENHA_VALIDA

TEXTO_DA_EMENTA = [
    "Introducao a Programacao - 60 horas",
    "Conteudo programatico: variaveis, condicionais, lacos e funcoes.",
    "Bibliografia basica: Pense em Python.",
]


def pdf_com_texto(linhas: list[str], *, paginas: int = 1) -> bytes:
    """PDF mínimo, montado à mão, com texto selecionável em cada página."""
    texto = " ".join(f"({linha}) Tj 0 -16 Td" for linha in linhas)
    conteudo = f"BT /F1 12 Tf 72 720 Td {texto} ET".encode()

    filhos = " ".join(f"{3 + 2 * i} 0 R" for i in range(paginas))
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{filhos}] /Count {paginas} >>".encode(),
    ]
    fonte = 3 + 2 * paginas
    for i in range(paginas):
        objetos.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {fonte} 0 R >> >> /Contents {4 + 2 * i} 0 R >>".encode()
        )
        objetos.append(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(conteudo), conteudo))
    objetos.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    saida = BytesIO()
    saida.write(b"%PDF-1.4\n")
    deslocamentos = []
    for numero, corpo in enumerate(objetos, start=1):
        deslocamentos.append(saida.tell())
        saida.write(b"%d 0 obj\n%s\nendobj\n" % (numero, corpo))
    xref = saida.tell()
    saida.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1))
    for deslocamento in deslocamentos:
        saida.write(b"%010d 00000 n \n" % deslocamento)
    saida.write(
        b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objetos) + 1, xref)
    )
    return saida.getvalue()


@pytest.fixture
def catalogo_seed(db: Session) -> None:
    academico.aplicar(db)


def _id(db: Session, modelo, nome: str) -> int:
    return db.execute(select(modelo.id).where(modelo.nome == nome)).scalar_one()


@pytest.fixture
def ufrpe(db: Session, catalogo_seed: None) -> int:
    return _id(db, Instituicao, "Universidade Federal Rural de Pernambuco")


@pytest.fixture
def bsi(db: Session, catalogo_seed: None) -> int:
    return _id(db, Curso, "Bacharelado em Sistemas de Informação")


def _siglas(cliente: TestClient, busca: str) -> list[str]:
    resposta = cliente.get("/api/v1/instituicoes", params={"busca": busca})
    assert resposta.status_code == 200, resposta.text
    return [instituicao["sigla"] for instituicao in resposta.json()]


# --------------------------------------------------------------------------
# Catálogo
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "busca",
    ["UFRPE", "ufrpe", "ufrp", "rural pernambuco", "Rúral", "federal rural", "pernanbuco rural"],
)
def test_busca_acha_a_ufrpe_do_jeito_que_o_aluno_digita(
    cliente: TestClient, catalogo_seed: None, busca: str
) -> None:
    """O critério da #185: sigla, sem acento, com acento sobrando e com erro."""
    assert _siglas(cliente, busca)[0] == "UFRPE"


def test_busca_nao_inventa_semelhanca(cliente: TestClient, catalogo_seed: None) -> None:
    # "rural" casa, "paraiba" não: o pior termo decide.
    assert "UFRPE" not in _siglas(cliente, "rural paraiba")
    assert _siglas(cliente, "xyzw") == []


def test_busca_por_palavra_comum_traz_varias(cliente: TestClient, catalogo_seed: None) -> None:
    assert {"UFRPE", "UFPE", "UPE", "UNICAP"} <= set(_siglas(cliente, "pernambuco"))


def test_sem_busca_lista_em_ordem_alfabetica(cliente: TestClient, catalogo_seed: None) -> None:
    nomes = [i["nome"] for i in cliente.get("/api/v1/instituicoes").json()]

    assert nomes == sorted(nomes)
    assert len(nomes) == len(academico.INSTITUICOES)


def test_limite_da_busca(cliente: TestClient, catalogo_seed: None) -> None:
    assert len(cliente.get("/api/v1/instituicoes", params={"limite": 2}).json()) == 2
    assert cliente.get("/api/v1/instituicoes", params={"limite": 50}).status_code == 422


def test_instituicao_digitada_por_aluno_nao_vira_sugestao(
    cliente: TestClient, db: Session, catalogo_seed: None
) -> None:
    db.add(Instituicao(nome="Faculdade Inventada do Recife"))
    db.commit()

    assert _siglas(cliente, "inventada") == []


def test_cursos_da_instituicao(cliente: TestClient, ufrpe: int) -> None:
    cursos = cliente.get(f"/api/v1/instituicoes/{ufrpe}/cursos").json()

    assert cursos == [
        {
            "id": cursos[0]["id"],
            "nome": "Bacharelado em Sistemas de Informação",
            "total_periodos": 8,
        }
    ]


def test_cursos_de_instituicao_fora_do_catalogo_responde_404(
    cliente: TestClient, db: Session
) -> None:
    digitada = Instituicao(nome="Digitada")
    db.add(digitada)
    db.commit()

    resposta = cliente.get(f"/api/v1/instituicoes/{digitada.id}/cursos")
    assert resposta.status_code == 404
    assert resposta.json()["erro"]["code"] == "instituicao_nao_encontrada"


def test_periodos_trazem_as_disciplinas_do_catalogo(
    cliente: TestClient, db: Session, bsi: int
) -> None:
    db.add_all(
        [
            Trilha(slug="a", nome="A", disciplina="Algoritmos", periodo=1, publicada=True),
            Trilha(slug="b", nome="B", disciplina="Algoritmos", periodo=1, publicada=True),
            Trilha(slug="c", nome="C", disciplina="Banco de Dados", periodo=3, publicada=True),
            Trilha(slug="d", nome="D", disciplina="Rascunho", periodo=1, publicada=False),
        ]
    )
    db.commit()

    periodos = cliente.get(f"/api/v1/cursos/{bsi}/periodos").json()

    assert [p["numero"] for p in periodos] == list(range(1, 9))
    assert periodos[0]["disciplinas"] == ["Algoritmos"]
    assert periodos[2]["disciplinas"] == ["Banco de Dados"]
    assert periodos[1]["disciplinas"] == []


def test_periodos_de_curso_inexistente_responde_404(cliente: TestClient) -> None:
    assert cliente.get("/api/v1/cursos/999/periodos").status_code == 404


def test_seed_e_idempotente_e_verifica_o_que_ja_existia(db: Session) -> None:
    # Um aluno digitou o nome completo antes do seed rodar.
    db.add(Instituicao(nome="universidade federal rural de pernambuco"))
    db.commit()

    academico.aplicar(db)
    academico.aplicar(db)

    ufrpes = (
        db.execute(
            select(Instituicao).where(
                func.lower(Instituicao.nome) == "universidade federal rural de pernambuco"
            )
        )
        .scalars()
        .all()
    )
    assert len(ufrpes) == 1 and ufrpes[0].verificada
    assert db.execute(select(func.count(Curso.id))).scalar_one() == 1


def test_normalizar() -> None:
    assert catalogo.normalizar("  Educação,  Ciência!") == "educacao ciencia"


# --------------------------------------------------------------------------
# POST /onboarding
# --------------------------------------------------------------------------

BASE = {"nivel_experiencia": "medio", "tipo_trilha": "mista"}


def _onboarding(cliente: TestClient, headers: dict[str, str], **dados):
    return cliente.post("/api/v1/onboarding", headers=headers, json={**BASE, **dados})


def test_onboarding_pelo_catalogo(
    cliente: TestClient, autenticado: dict[str, str], ufrpe: int, bsi: int
) -> None:
    resposta = _onboarding(cliente, autenticado, instituicao_id=ufrpe, curso_id=bsi, periodo=2)

    assert resposta.status_code == 200, resposta.text
    perfil = resposta.json()
    assert perfil["instituicao"] == "Universidade Federal Rural de Pernambuco"
    assert perfil["curso"] == "Bacharelado em Sistemas de Informação"
    assert (perfil["periodo"], perfil["tipo_trilha"], perfil["nivel_experiencia"]) == (
        2,
        "mista",
        "medio",
    )
    assert perfil["onboarding_concluido_em"] is not None


def test_onboarding_com_texto_livre_nao_trava(
    cliente: TestClient, autenticado: dict[str, str], catalogo_seed: None
) -> None:
    """O critério da #186."""
    resposta = _onboarding(
        cliente,
        autenticado,
        instituicao="Faculdade Nova do Agreste",
        curso="Engenharia de Software",
    )

    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["instituicao"] == "Faculdade Nova do Agreste"
    assert _siglas(cliente, "agreste") == []


def test_sigla_digitada_cai_na_instituicao_do_catalogo(
    cliente: TestClient, autenticado: dict[str, str], db: Session, ufrpe: int
) -> None:
    perfil = _onboarding(cliente, autenticado, instituicao="ufrpe").json()

    assert perfil["instituicao"] == "Universidade Federal Rural de Pernambuco"
    assert db.execute(select(func.count(Instituicao.id))).scalar_one() == len(
        academico.INSTITUICOES
    )


def test_curso_pelo_id_basta(cliente: TestClient, autenticado: dict[str, str], bsi: int) -> None:
    perfil = _onboarding(cliente, autenticado, curso_id=bsi).json()

    assert perfil["instituicao"] == "Universidade Federal Rural de Pernambuco"


def test_curso_de_outra_instituicao_e_recusado(
    cliente: TestClient, autenticado: dict[str, str], db: Session, bsi: int
) -> None:
    ufpe = _id(db, Instituicao, "Universidade Federal de Pernambuco")

    resposta = _onboarding(cliente, autenticado, instituicao_id=ufpe, curso_id=bsi)

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["code"] == "curso_de_outra_instituicao"


@pytest.mark.parametrize(
    ("dados", "codigo"),
    [
        ({"instituicao_id": 999}, "instituicao_nao_encontrada"),
        ({"curso_id": 999}, "curso_nao_encontrado"),
    ],
)
def test_id_fora_do_catalogo_e_recusado(
    cliente: TestClient, autenticado: dict[str, str], catalogo_seed: None, dados, codigo
) -> None:
    resposta = _onboarding(cliente, autenticado, **dados)

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["code"] == codigo


def test_periodo_alem_do_curso_e_recusado(
    cliente: TestClient, autenticado: dict[str, str], bsi: int
) -> None:
    resposta = _onboarding(cliente, autenticado, curso_id=bsi, periodo=10)

    assert resposta.status_code == 422
    assert resposta.json()["erro"]["code"] == "periodo_fora_do_curso"


@pytest.mark.parametrize(
    "dados",
    [
        {"instituicao_id": 1, "instituicao": "UFRPE"},
        {"curso_id": 1, "curso": "BSI", "instituicao": "UFRPE"},
        {"curso": "Sistemas de Informação"},
        {"nivel_experiencia": None},
    ],
)
def test_onboarding_mal_formado_e_recusado(
    cliente: TestClient, autenticado: dict[str, str], dados
) -> None:
    assert _onboarding(cliente, autenticado, **dados).status_code == 422


def test_refazer_o_onboarding_guarda_a_primeira_conclusao(
    cliente: TestClient, autenticado: dict[str, str], db: Session, usuario: Usuario
) -> None:
    primeira = _onboarding(cliente, autenticado).json()["onboarding_concluido_em"]

    segunda = _onboarding(cliente, autenticado, tipo_trilha="livre").json()

    assert segunda["onboarding_concluido_em"] == primeira
    assert segunda["tipo_trilha"] == "livre"


def test_onboarding_sem_instituicao_limpa_a_anterior(
    cliente: TestClient, autenticado: dict[str, str], ufrpe: int
) -> None:
    """É o retrato completo: o que não veio fica vazio."""
    _onboarding(cliente, autenticado, instituicao_id=ufrpe, periodo=3)

    perfil = _onboarding(cliente, autenticado).json()

    assert (perfil["instituicao"], perfil["periodo"]) == (None, None)


def test_onboarding_exige_autenticacao(cliente: TestClient) -> None:
    assert cliente.post("/api/v1/onboarding", json=BASE).status_code == 401


def test_perfil_de_quem_nao_fez_onboarding(
    cliente: TestClient, autenticado: dict[str, str]
) -> None:
    corpo = cliente.get("/api/v1/usuarios/me", headers=autenticado).json()
    assert corpo["onboarding_concluido_em"] is None


# --------------------------------------------------------------------------
# Ementa
# --------------------------------------------------------------------------


@pytest.fixture
def midia(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.setattr(settings, "diretorio_midia", str(tmp_path))
    yield tmp_path


def _enviar(cliente: TestClient, headers: dict[str, str], conteudo: bytes, nome="ementa.pdf"):
    return cliente.post(
        "/api/v1/ementas",
        headers=headers,
        files={"arquivo": (nome, conteudo, "application/pdf")},
    )


def _status(cliente: TestClient, headers: dict[str, str], ementa_id: int) -> dict:
    resposta = cliente.get(f"/api/v1/ementas/{ementa_id}", headers=headers)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def test_ementa_responde_202_e_o_texto_e_extraido_depois(
    cliente: TestClient, autenticado: dict[str, str], db: Session, midia: Path
) -> None:
    """O critério da #187."""
    resposta = _enviar(cliente, autenticado, pdf_com_texto(TEXTO_DA_EMENTA))

    assert resposta.status_code == 202, resposta.text
    corpo = resposta.json()
    assert corpo["status"] == "pendente"
    assert resposta.headers["location"] == f"/api/v1/ementas/{corpo['id']}"

    # O TestClient roda a tarefa em segundo plano antes de devolver a resposta.
    depois = _status(cliente, autenticado, corpo["id"])
    assert (depois["status"], depois["paginas"], depois["erro"]) == ("processada", 1, None)
    assert depois["nome_original"] == "ementa.pdf"

    ementa = db.get(Ementa, corpo["id"])
    db.refresh(ementa)
    assert "Conteudo programatico" in ementa.texto_extraido
    assert "texto_extraido" not in depois


def test_ementa_fica_fora_da_pasta_publica(
    cliente: TestClient, autenticado: dict[str, str], db: Session, midia: Path, usuario: Usuario
) -> None:
    ementa_id = _enviar(cliente, autenticado, pdf_com_texto(TEXTO_DA_EMENTA)).json()["id"]
    caminho = db.get(Ementa, ementa_id).arquivo_path

    assert caminho.startswith(f"ementas/{usuario.id}/")
    assert (midia / caminho).exists()
    assert cliente.get(f"/media/{caminho}").status_code == 404
    assert cliente.get(f"/media/avatares/../{caminho}").status_code == 404


def test_ementa_guarda_o_curso_e_o_periodo_do_aluno(
    cliente: TestClient, autenticado: dict[str, str], db: Session, midia: Path, bsi: int
) -> None:
    _onboarding(cliente, autenticado, curso_id=bsi, periodo=1)

    ementa_id = _enviar(cliente, autenticado, pdf_com_texto(TEXTO_DA_EMENTA)).json()["id"]

    ementa = db.get(Ementa, ementa_id)
    assert (ementa.curso_id, ementa.periodo) == (bsi, 1)


def test_arquivo_que_nao_e_pdf_e_recusado(
    cliente: TestClient, autenticado: dict[str, str], midia: Path
) -> None:
    resposta = _enviar(cliente, autenticado, b"\x89PNG\r\n\x1a\nnao sou pdf", "grade.pdf")

    assert resposta.status_code == 415
    assert resposta.json()["erro"]["code"] == "ementa_invalida"
    assert not (midia / "ementas").exists()


def test_ementa_acima_do_limite_e_recusada(
    cliente: TestClient,
    autenticado: dict[str, str],
    midia: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "tamanho_maximo_ementa", 100)

    resposta = _enviar(cliente, autenticado, pdf_com_texto(TEXTO_DA_EMENTA))

    assert resposta.status_code == 413
    assert resposta.json()["erro"]["code"] == "ementa_grande_demais"


def _falha(cliente: TestClient, headers: dict[str, str], conteudo: bytes) -> str:
    ementa_id = _enviar(cliente, headers, conteudo).json()["id"]
    corpo = _status(cliente, headers, ementa_id)
    assert corpo["status"] == "falhou"
    return corpo["erro"]


def test_pdf_sem_texto_falha_com_o_motivo(
    cliente: TestClient, autenticado: dict[str, str], midia: Path
) -> None:
    """Ementa escaneada é imagem: sem OCR (#38), não há texto para ler."""
    assert "escaneada" in _falha(cliente, autenticado, pdf_com_texto([]))


def test_pdf_corrompido_falha_com_o_motivo(
    cliente: TestClient, autenticado: dict[str, str], midia: Path
) -> None:
    assert _falha(cliente, autenticado, b"%PDF-1.4 grade de teste")


def test_pdf_com_senha_falha_com_o_motivo(
    cliente: TestClient, autenticado: dict[str, str], midia: Path
) -> None:
    escritor = PdfWriter()
    escritor.add_blank_page(width=612, height=792)
    escritor.encrypt("segredo", algorithm="RC4-128")
    saida = BytesIO()
    escritor.write(saida)

    assert "senha" in _falha(cliente, autenticado, saida.getvalue())


def test_pdf_com_paginas_demais_falha(
    cliente: TestClient,
    autenticado: dict[str, str],
    midia: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "maximo_paginas_ementa", 2)

    erro = _falha(cliente, autenticado, pdf_com_texto(TEXTO_DA_EMENTA, paginas=3))

    assert "2 páginas" in erro


def test_mesma_ementa_reaproveita_o_texto(
    cliente: TestClient,
    autenticado: dict[str, str],
    db: Session,
    midia: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf = pdf_com_texto(TEXTO_DA_EMENTA)
    _enviar(cliente, autenticado, pdf)

    # Se o segundo envio passasse pelo PDF, isto estouraria.
    def nao_deveria_ler(*_args, **_kwargs):
        raise AssertionError("leu o PDF de novo")

    monkeypatch.setattr("app.services.ementas._extrair_texto", nao_deveria_ler)
    segunda = _enviar(cliente, autenticado, pdf).json()

    assert segunda["status"] == "processada"
    assert "Conteudo programatico" in db.get(Ementa, segunda["id"]).texto_extraido


def test_ementa_de_outro_aluno_responde_404(
    cliente: TestClient, autenticado: dict[str, str], db: Session, midia: Path
) -> None:
    ementa_id = _enviar(cliente, autenticado, pdf_com_texto(TEXTO_DA_EMENTA)).json()["id"]
    servico_auth.registrar(
        db, email="bia@ufrpe.br", senha=SENHA_VALIDA, username="bia", nome_exibicao="Bia"
    )
    login = cliente.post(
        "/api/v1/auth/login", json={"email": "bia@ufrpe.br", "senha": SENHA_VALIDA}
    ).json()
    outra = {"Authorization": f"Bearer {login['access_token']}"}

    resposta = cliente.get(f"/api/v1/ementas/{ementa_id}", headers=outra)

    assert resposta.status_code == 404
    assert resposta.json()["erro"]["code"] == "ementa_nao_encontrada"


def test_ementa_exige_autenticacao(cliente: TestClient, midia: Path) -> None:
    resposta = cliente.post(
        "/api/v1/ementas", files={"arquivo": ("e.pdf", b"%PDF-1.4", "application/pdf")}
    )
    assert resposta.status_code == 401


def test_processar_ignora_ementa_que_ja_saiu_de_pendente(
    sessao_factory, db: Session, usuario: Usuario, midia: Path
) -> None:
    """Chamar duas vezes (um retry, uma tarefa duplicada) não refaz a leitura."""
    from app.ia.eco import Eco
    from app.services import ementas

    ementa = Ementa(usuario_id=usuario.id, arquivo_path="x.pdf", status=StatusEmenta.falhou)
    db.add(ementa)
    db.commit()

    ementas.processar(sessao_factory, Eco(), ementa.id)

    db.refresh(ementa)
    assert ementa.status is StatusEmenta.falhou


def test_expurgo_da_conta_apaga_as_ementas(
    cliente: TestClient, autenticado: dict[str, str], db: Session, usuario: Usuario, midia: Path
) -> None:
    _enviar(cliente, autenticado, pdf_com_texto(TEXTO_DA_EMENTA))
    assert (midia / "ementas" / str(usuario.id)).exists()

    db.refresh(usuario)
    usuario.exclusao_agendada_para = datetime.now(UTC) - timedelta(days=1)
    db.commit()
    conta.expurgar_vencidas(db)

    assert not (midia / "ementas" / str(usuario.id)).exists()
