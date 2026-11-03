"""O que faltava da #33: anexos nas mensagens e o resumo do que sai da janela."""

import asyncio
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.seguranca import criar_access_token
from app.models import AnexoChat, Conversa, MensagemChat, PapelMensagem, Usuario
from app.services import anexos, conta, resumo_chat
from tests.test_chat import ProvedorFalso, enviar, provedor  # noqa: F401 - fixture

URL = "/api/v1/chat"


@pytest.fixture(autouse=True)
def midia_temporaria(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "diretorio_midia", str(tmp_path))
    return tmp_path


def subir(cliente: TestClient, headers: dict[str, str], nome: str, conteudo: bytes):
    return cliente.post(f"{URL}/anexos", files={"arquivo": (nome, conteudo)}, headers=headers)


def png() -> bytes:
    saida = BytesIO()
    Image.new("RGB", (4, 4), "red").save(saida, "PNG")
    return saida.getvalue()


def pdf() -> bytes:
    escritor = PdfWriter()
    escritor.add_blank_page(width=72, height=72)
    saida = BytesIO()
    escritor.write(saida)
    return saida.getvalue()


# --- upload e validação -------------------------------------------------------------------


def test_tipos_aceitos_saem_do_conteudo(cliente: TestClient, autenticado: dict[str, str]) -> None:
    codigo = subir(cliente, autenticado, "lacos.py", b"for i in range(3):\n    print(i)\n")
    imagem = subir(cliente, autenticado, "tela.png", png())
    documento = subir(cliente, autenticado, "lista.pdf", pdf())
    # Um PNG com nome de texto continua sendo imagem.
    disfarcado = subir(cliente, autenticado, "notas.txt", png())

    assert codigo.status_code == 201
    assert (codigo.json()["tipo"], codigo.json()["nome"]) == ("texto", "lacos.py")
    assert imagem.json()["tipo"] == "imagem"
    assert documento.json()["tipo"] == "pdf"
    assert disfarcado.json()["tipo"] == "imagem"


@pytest.mark.parametrize(
    ("nome", "conteudo"),
    [
        ("programa.exe", b"MZ\x90\x00binario"),
        ("falso.txt", b"texto\x00com byte nulo"),
        ("latin1.txt", "ação".encode("latin-1")),
        ("vazio.txt", b""),
    ],
)
def test_arquivo_recusado(
    cliente: TestClient, autenticado: dict[str, str], nome: str, conteudo: bytes
) -> None:
    resposta = subir(cliente, autenticado, nome, conteudo)

    assert resposta.status_code == 415
    assert resposta.json()["erro"]["code"] == "anexo_invalido"


def test_anexo_grande_demais(
    cliente: TestClient, autenticado: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "chat_anexo_tamanho_maximo", 10)

    resposta = subir(cliente, autenticado, "a.txt", b"x" * 11)

    assert resposta.status_code == 413


def test_nome_do_arquivo_nao_escolhe_o_caminho(
    cliente: TestClient, autenticado: dict[str, str], db: Session, midia_temporaria: Path
) -> None:
    resposta = subir(cliente, autenticado, "../../segredo.txt", b"oi")

    anexo = db.get(AnexoChat, resposta.json()["id"])
    assert anexo.nome == "segredo.txt"
    assert (midia_temporaria / "chat" / anexo.arquivo).read_bytes() == b"oi"


# --- na mensagem --------------------------------------------------------------------------


def test_texto_do_anexo_vai_para_o_tutor_e_fica_na_mensagem(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorFalso,  # noqa: F811
    db: Session,
) -> None:
    codigo = subir(cliente, autenticado, "erro.py", b"print(x)").json()
    imagem = subir(cliente, autenticado, "tela.png", png()).json()

    eventos = enviar(
        cliente,
        autenticado,
        "Por que dá NameError?",
        anexo_ids=[codigo["id"], imagem["id"]],
    )
    conversa_id = eventos[0][1]["conversa_id"]

    pergunta = provedor.contexto[-1].conteudo
    assert pergunta.startswith("Por que dá NameError?")
    assert 'Anexo "erro.py":\n```\nprint(x)\n```' in pergunta
    assert '(O aluno anexou "tela.png", que você não consegue ler.)' in pergunta
    mensagens = cliente.get(f"{URL}/conversas/{conversa_id}/mensagens", headers=autenticado)
    primeira = mensagens.json()["itens"][0]
    # O que fica gravado é o que o aluno escreveu; o anexo vem ao lado.
    assert primeira["conteudo"] == "Por que dá NameError?"
    assert [a["nome"] for a in primeira["anexos"]] == ["erro.py", "tela.png"]


def test_anexo_nao_serve_duas_vezes_nem_e_de_outro(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorFalso,  # noqa: F811
    db: Session,
) -> None:
    usado = subir(cliente, autenticado, "a.py", b"1").json()["id"]
    enviar(cliente, autenticado, "primeira", anexo_ids=[usado])
    dona = Usuario(email="bia@ufrpe.br", username="bia", nome_exibicao="Bia")
    db.add(dona)
    db.commit()
    alheio = subir(
        cliente, {"Authorization": f"Bearer {criar_access_token(dona.id)}"}, "b.py", b"2"
    ).json()["id"]

    for ids in ([usado], [alheio]):
        resposta = cliente.post(
            f"{URL}/mensagens", json={"conteudo": "oi", "anexo_ids": ids}, headers=autenticado
        )
        assert resposta.status_code == 404
        assert resposta.json()["erro"]["code"] == "anexo_nao_encontrado"


def test_anexos_demais_por_mensagem(cliente: TestClient, autenticado: dict[str, str]) -> None:
    resposta = cliente.post(
        f"{URL}/mensagens", json={"conteudo": "oi", "anexo_ids": [1, 2, 3, 4]}, headers=autenticado
    )

    assert resposta.status_code == 422


# --- download e exclusão ------------------------------------------------------------------


def test_download_so_do_dono_e_sempre_como_arquivo(
    cliente: TestClient, autenticado: dict[str, str], db: Session
) -> None:
    anexo = subir(cliente, autenticado, "pagina.html", b"<script>alert(1)</script>").json()
    dona = Usuario(email="bia@ufrpe.br", username="bia", nome_exibicao="Bia")
    db.add(dona)
    db.commit()

    meu = cliente.get(f"{URL}/anexos/{anexo['id']}", headers=autenticado)
    alheio = cliente.get(
        f"{URL}/anexos/{anexo['id']}",
        headers={"Authorization": f"Bearer {criar_access_token(dona.id)}"},
    )

    assert meu.content == b"<script>alert(1)</script>"
    assert meu.headers["content-type"] == "application/octet-stream"
    assert meu.headers["content-disposition"].startswith("attachment")
    assert meu.headers["x-content-type-options"] == "nosniff"
    assert alheio.status_code == 404


def test_desistir_do_anexo_antes_de_enviar(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorFalso,  # noqa: F811
    midia_temporaria: Path,
) -> None:
    solto = subir(cliente, autenticado, "a.py", b"1").json()["id"]
    usado = subir(cliente, autenticado, "b.py", b"2").json()["id"]
    enviar(cliente, autenticado, "oi", anexo_ids=[usado])

    assert cliente.delete(f"{URL}/anexos/{solto}", headers=autenticado).status_code == 204
    assert cliente.delete(f"{URL}/anexos/{usado}", headers=autenticado).status_code == 409
    assert len(list((midia_temporaria / "chat").iterdir())) == 1


def test_apagar_a_conversa_apaga_os_anexos_e_os_arquivos(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorFalso,  # noqa: F811
    db: Session,
    midia_temporaria: Path,
) -> None:
    anexo = subir(cliente, autenticado, "a.py", b"1").json()["id"]
    conversa_id = enviar(cliente, autenticado, "oi", anexo_ids=[anexo])[0][1]["conversa_id"]

    resposta = cliente.delete(f"{URL}/conversas/{conversa_id}", headers=autenticado)

    assert resposta.status_code == 204
    db.expire_all()
    assert db.get(AnexoChat, anexo) is None
    assert list((midia_temporaria / "chat").iterdir()) == []


# --- resumo do que saiu da janela ---------------------------------------------------------


def test_o_que_sai_da_janela_vira_resumo(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorFalso,  # noqa: F811
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "chat_janela_historico", 2)
    conversa_id = enviar(cliente, autenticado, "primeira")[0][1]["conversa_id"]
    db.expire_all()
    assert db.get(Conversa, conversa_id).resumo is None

    enviar(cliente, autenticado, "segunda", conversa_id=conversa_id)

    db.expire_all()
    conversa = db.get(Conversa, conversa_id)
    primeiras = db.scalars(
        select(MensagemChat.id)
        .where(MensagemChat.conversa_id == conversa_id)
        .order_by(MensagemChat.id)
        .limit(2)
    ).all()
    assert conversa.resumo == "Recursão é uma função que chama a si mesma."
    assert conversa.resumo_ate_id == primeiras[-1]
    pedido = provedor.chamadas[-1][0][1].conteudo
    assert "aluno: primeira" in pedido and "tutor: Recursão" in pedido


def test_resumo_com_a_ia_fora_fica_para_depois(
    sessao_factory: sessionmaker[Session], usuario: Usuario, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "chat_janela_historico", 2)
    with sessao_factory() as db:
        conversa = Conversa(usuario_id=usuario.id, titulo="t", resumo="antigo")
        conversa.mensagens = [
            MensagemChat(papel=PapelMensagem.usuario, conteudo=str(i)) for i in range(4)
        ]
        db.add(conversa)
        db.commit()
        conversa_id = conversa.id
    fora = ProvedorFalso()
    fora.falhar_antes = True

    resumiu = asyncio.run(resumo_chat.atualizar(sessao_factory, fora, conversa_id))

    assert resumiu is False
    with sessao_factory() as db:
        assert db.get(Conversa, conversa_id).resumo == "antigo"


def test_para_o_modelo_sem_anexo_e_so_a_pergunta() -> None:
    assert anexos.para_o_modelo("oi", []) == "oi"


def test_expurgo_da_conta_apaga_os_arquivos_dos_anexos(
    cliente: TestClient,
    autenticado: dict[str, str],
    db: Session,
    usuario: Usuario,
    midia_temporaria: Path,
) -> None:
    subir(cliente, autenticado, "a.py", b"1")
    db.refresh(usuario)
    usuario.exclusao_agendada_para = datetime.now(UTC) - timedelta(days=1)
    db.commit()

    assert conta.expurgar_vencidas(db) == 1

    assert list((midia_temporaria / "chat").iterdir()) == []
