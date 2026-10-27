"""Testes do perfil (#27): preferências, modo de trilha, foto e perfil público.

O que mais pesa aqui é a autorização: toda escrita é sobre `/me`, e o perfil
público não pode carregar dado que o próprio aluno não veria no ranking.
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.core.config import settings
from app.main import app
from app.models import Atividade, Modulo, TipoAtividade, TipoTrilha, Trilha, Usuario
from app.services import auth as servico_auth
from app.services import avatar, conta, progresso
from tests.conftest import SENHA_VALIDA


def entrar(cliente: TestClient, email: str) -> dict[str, str]:
    resposta = cliente.post("/api/v1/auth/login", json={"email": email, "senha": SENHA_VALIDA})
    assert resposta.status_code == 200, resposta.text
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


@pytest.fixture
def outro(db: Session) -> Usuario:
    """Um segundo aluno, para conferir o que um vê (e altera) do outro."""
    return servico_auth.registrar(
        db, email="bia@ufrpe.br", senha=SENHA_VALIDA, username="bia", nome_exibicao="Bia Souza"
    )


# --------------------------------------------------------------------------
# Nível no perfil
# --------------------------------------------------------------------------


def test_perfil_traz_o_nivel_calculado_pelo_servidor(
    cliente: TestClient, autenticado: dict[str, str], db: Session, usuario: Usuario
) -> None:
    usuario.xp_total = 120  # nível 2 começa em 50; o 3, em 200
    db.commit()

    corpo = cliente.get("/api/v1/usuarios/me", headers=autenticado).json()

    assert (corpo["nivel"], corpo["xp_no_nivel"], corpo["xp_para_proximo"]) == (2, 70, 80)


# --------------------------------------------------------------------------
# Preferências
# --------------------------------------------------------------------------


def test_preferencias_comecam_no_padrao(cliente: TestClient, autenticado: dict[str, str]) -> None:
    corpo = cliente.get("/api/v1/usuarios/me", headers=autenticado).json()

    assert corpo["preferencias"] == {
        "tamanho_fonte": "normal",
        "alto_contraste": False,
        "reduzir_animacoes": False,
    }


def test_preferencias_mudam_so_o_que_foi_enviado(
    cliente: TestClient, autenticado: dict[str, str]
) -> None:
    cliente.patch(
        "/api/v1/usuarios/me/preferencias", headers=autenticado, json={"tamanho_fonte": "alta"}
    )
    resposta = cliente.patch(
        "/api/v1/usuarios/me/preferencias", headers=autenticado, json={"alto_contraste": True}
    )

    assert resposta.status_code == 200
    assert resposta.json() == {
        "tamanho_fonte": "alta",
        "alto_contraste": True,
        "reduzir_animacoes": False,
    }


def test_preferencias_acompanham_a_conta_em_outra_sessao(
    cliente: TestClient, autenticado: dict[str, str], usuario: Usuario
) -> None:
    """O critério da #179: ligou num aparelho, encontra ligado no outro."""
    cliente.patch(
        "/api/v1/usuarios/me/preferencias", headers=autenticado, json={"alto_contraste": True}
    )

    outro_aparelho = entrar(cliente, usuario.email)
    corpo = cliente.get("/api/v1/usuarios/me", headers=outro_aparelho).json()

    assert corpo["preferencias"]["alto_contraste"] is True


def test_preferencia_com_valor_desconhecido_e_recusada(
    cliente: TestClient, autenticado: dict[str, str]
) -> None:
    resposta = cliente.patch(
        "/api/v1/usuarios/me/preferencias", headers=autenticado, json={"tamanho_fonte": "enorme"}
    )

    assert resposta.status_code == 422


# --------------------------------------------------------------------------
# Modo de trilha
# --------------------------------------------------------------------------


@pytest.fixture
def trilha_do_periodo(db: Session) -> Trilha:
    """Trilha do 1º período com três passos."""
    return _trilha(db, slug="logica", periodo=1)


def _trilha(db: Session, *, slug: str, periodo: int | None) -> Trilha:
    trilha = Trilha(slug=slug, nome=slug.title(), disciplina="Algoritmos", periodo=periodo)
    trilha.publicada = True
    for ordem in (1, 2, 3):
        modulo = Modulo(ordem=ordem, titulo=f"Passo {ordem}", descricao=f"Conteúdo {ordem}")
        modulo.atividades.append(
            Atividade(
                ordem=1,
                tipo=TipoAtividade.terminal,
                enunciado="Rode o Python",
                comando_esperado="python --version",
                xp=10,
            )
        )
        trilha.modulos.append(modulo)
    db.add(trilha)
    db.commit()
    return trilha


def _estados(cliente: TestClient, headers: dict[str, str], slug: str) -> list[str]:
    corpo = cliente.get(f"/api/v1/trilhas/{slug}", headers=headers).json()
    return [modulo["status"] for modulo in corpo["modulos"]]


def _trocar(cliente: TestClient, headers: dict[str, str], modo: str) -> dict:
    resposta = cliente.patch(
        "/api/v1/usuarios/me/trilha", headers=headers, json={"tipo_trilha": modo}
    )
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def test_trocar_modo_devolve_o_perfil_atualizado(
    cliente: TestClient, autenticado: dict[str, str]
) -> None:
    assert _trocar(cliente, autenticado, "livre")["tipo_trilha"] == "livre"


def test_modo_desconhecido_e_recusado(cliente: TestClient, autenticado: dict[str, str]) -> None:
    resposta = cliente.patch(
        "/api/v1/usuarios/me/trilha", headers=autenticado, json={"tipo_trilha": "turbo"}
    )
    assert resposta.status_code == 422


def test_guiada_segue_a_ordem(
    cliente: TestClient, autenticado: dict[str, str], trilha_do_periodo: Trilha
) -> None:
    assert _estados(cliente, autenticado, "logica") == ["em-andamento", "bloqueado", "bloqueado"]


def test_livre_libera_todos_os_passos(
    cliente: TestClient, autenticado: dict[str, str], trilha_do_periodo: Trilha
) -> None:
    _trocar(cliente, autenticado, "livre")

    assert _estados(cliente, autenticado, "logica") == ["em-andamento"] * 3
    assert cliente.get("/api/v1/trilhas/logica/passos/3", headers=autenticado).status_code == 200


def test_livre_libera_tambem_a_atividade_do_passo(
    cliente: TestClient, autenticado: dict[str, str], trilha_do_periodo: Trilha
) -> None:
    """A submissão confere o desbloqueio pela mesma regra da tela."""
    ultimo = max(trilha_do_periodo.modulos, key=lambda m: m.ordem)
    rota = f"/api/v1/atividades/{ultimo.atividades[0].id}/submissoes"
    corpo = {"conteudo": "python --version"}

    assert cliente.post(rota, headers=autenticado, json=corpo).status_code == 403

    _trocar(cliente, autenticado, "livre")

    assert cliente.post(rota, headers=autenticado, json=corpo).status_code == 201


def test_voltar_para_guiada_nao_perde_o_que_foi_feito_fora_de_ordem(
    cliente: TestClient,
    autenticado: dict[str, str],
    db: Session,
    usuario: Usuario,
    trilha_do_periodo: Trilha,
) -> None:
    """O critério da #180."""
    _trocar(cliente, autenticado, "livre")
    terceiro = next(m for m in trilha_do_periodo.modulos if m.ordem == 3)
    progresso.concluir_passo(db, usuario_id=usuario.id, trilha=trilha_do_periodo, modulo=terceiro)

    _trocar(cliente, autenticado, "guiada")

    # O 3 continua fechado; o 2 é o próximo da ordem e está aberto.
    assert _estados(cliente, autenticado, "logica") == ["em-andamento", "bloqueado", "concluido"]


def test_mista_segue_a_ordem_so_no_periodo_do_aluno(
    cliente: TestClient, autenticado: dict[str, str], db: Session, trilha_do_periodo: Trilha
) -> None:
    _trilha(db, slug="git", periodo=3)
    cliente.patch("/api/v1/usuarios/me", headers=autenticado, json={"periodo": 1})
    _trocar(cliente, autenticado, "mista")

    assert _estados(cliente, autenticado, "logica") == ["em-andamento", "bloqueado", "bloqueado"]
    assert _estados(cliente, autenticado, "git") == ["em-andamento"] * 3


def test_mista_sem_periodo_segue_a_ordem(
    cliente: TestClient, autenticado: dict[str, str], trilha_do_periodo: Trilha
) -> None:
    _trocar(cliente, autenticado, "mista")

    assert _estados(cliente, autenticado, "logica") == ["em-andamento", "bloqueado", "bloqueado"]


def test_modo_de_um_aluno_nao_muda_o_que_o_visitante_ve(
    cliente: TestClient, autenticado: dict[str, str], trilha_do_periodo: Trilha
) -> None:
    _trocar(cliente, autenticado, "livre")

    assert _estados(cliente, {}, "logica") == ["em-andamento", "bloqueado", "bloqueado"]


def test_onboarding_pelo_patch_do_perfil_usa_a_mesma_regra(
    cliente: TestClient, autenticado: dict[str, str], trilha_do_periodo: Trilha
) -> None:
    cliente.patch("/api/v1/usuarios/me", headers=autenticado, json={"tipo_trilha": "livre"})

    assert _estados(cliente, autenticado, "logica") == ["em-andamento"] * 3


def test_segue_ordem_por_modo() -> None:
    trilha = Trilha(slug="x", nome="X", disciplina="Y", periodo=2)
    aluno = Usuario(tipo_trilha=TipoTrilha.mista, periodo=2)

    assert progresso.segue_ordem(trilha, None) is True
    assert progresso.segue_ordem(trilha, aluno) is True
    aluno.periodo = 5
    assert progresso.segue_ordem(trilha, aluno) is False
    aluno.tipo_trilha = TipoTrilha.livre
    assert progresso.segue_ordem(trilha, aluno) is False


# --------------------------------------------------------------------------
# Foto do perfil
# --------------------------------------------------------------------------


@pytest.fixture
def midia(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Pasta de mídia descartável, também para o `/media/avatares` servir dela."""
    monkeypatch.setattr(settings, "diretorio_midia", str(tmp_path))
    pasta = tmp_path / "avatares"
    pasta.mkdir()
    montagem = next(rota for rota in app.routes if getattr(rota, "name", None) == "avatares")
    monkeypatch.setattr(montagem.app, "all_directories", [pasta])
    yield pasta


def _imagem(formato: str = "PNG", tamanho: tuple[int, int] = (400, 300), **extra) -> bytes:
    saida = BytesIO()
    Image.new("RGB", tamanho, (30, 120, 200)).save(saida, format=formato, **extra)
    return saida.getvalue()


def _enviar(cliente: TestClient, headers: dict[str, str], conteudo: bytes, nome="foto.png"):
    return cliente.put(
        "/api/v1/usuarios/me/avatar",
        headers=headers,
        files={"arquivo": (nome, conteudo, "image/png")},
    )


def test_avatar_e_salvo_quadrado_em_webp_e_servido(
    cliente: TestClient, autenticado: dict[str, str], midia: Path
) -> None:
    resposta = _enviar(cliente, autenticado, _imagem())

    assert resposta.status_code == 200, resposta.text
    url = resposta.json()["avatar_url"]
    assert url.startswith("/media/avatares/") and url.endswith(".webp")

    servida = cliente.get(url)
    assert servida.status_code == 200
    assert servida.headers["content-type"] == "image/webp"
    with Image.open(BytesIO(servida.content)) as salva:
        assert salva.size == (avatar.LADO, avatar.LADO)


def test_avatar_sai_sem_o_exif_da_original(
    cliente: TestClient, autenticado: dict[str, str], midia: Path
) -> None:
    """O critério da #181: a localização da foto original não vai junto."""
    exif = Image.Exif()
    exif[0x8825] = {2: (8.0, 3.0, 0.0)}  # GPSInfo com uma latitude
    exif[0x010F] = "Câmera do celular"  # Make
    original = _imagem("JPEG", exif=exif.tobytes())
    with Image.open(BytesIO(original)) as conferida:
        assert conferida.getexif()  # o teste só vale se a original tinha EXIF

    url = _enviar(cliente, autenticado, original, "foto.jpg").json()["avatar_url"]

    with Image.open(midia / Path(url).name) as salva:
        assert not salva.getexif()
        assert "exif" not in salva.info


def test_pdf_renomeado_para_png_e_recusado(
    cliente: TestClient, autenticado: dict[str, str], midia: Path
) -> None:
    resposta = _enviar(cliente, autenticado, b"%PDF-1.7\n1 0 obj << >> endobj\n%%EOF")

    assert resposta.status_code == 415
    assert resposta.json()["erro"]["code"] == "avatar_invalido"
    assert list(midia.iterdir()) == []


def test_formato_de_imagem_fora_da_lista_e_recusado(
    cliente: TestClient, autenticado: dict[str, str], midia: Path
) -> None:
    assert _enviar(cliente, autenticado, _imagem("BMP"), "foto.bmp").status_code == 415


def test_imagem_truncada_e_recusada(
    cliente: TestClient, autenticado: dict[str, str], midia: Path
) -> None:
    assert _enviar(cliente, autenticado, _imagem()[:200]).status_code == 415


def test_avatar_acima_do_limite_e_recusado(
    cliente: TestClient,
    autenticado: dict[str, str],
    midia: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "tamanho_maximo_avatar", 1024)

    resposta = _enviar(cliente, autenticado, _imagem(tamanho=(800, 800)) + b"\0" * 2048)

    assert resposta.status_code == 413
    assert resposta.json()["erro"]["code"] == "avatar_grande_demais"


def test_imagem_com_resolucao_absurda_e_recusada(
    cliente: TestClient,
    autenticado: dict[str, str],
    midia: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Poucos bytes, muitos pixels: o limite de tamanho sozinho não pega."""
    monkeypatch.setattr(avatar, "MAXIMO_DE_PIXELS", 100 * 100)

    assert _enviar(cliente, autenticado, _imagem(tamanho=(200, 200))).status_code == 415


def test_trocar_o_avatar_apaga_o_arquivo_anterior(
    cliente: TestClient, autenticado: dict[str, str], midia: Path
) -> None:
    primeira = _enviar(cliente, autenticado, _imagem()).json()["avatar_url"]
    segunda = _enviar(cliente, autenticado, _imagem()).json()["avatar_url"]

    assert primeira != segunda
    assert [arquivo.name for arquivo in midia.iterdir()] == [Path(segunda).name]


def test_remover_o_avatar_volta_para_as_iniciais(
    cliente: TestClient, autenticado: dict[str, str], midia: Path
) -> None:
    _enviar(cliente, autenticado, _imagem())

    resposta = cliente.delete("/api/v1/usuarios/me/avatar", headers=autenticado)

    assert resposta.status_code == 200
    assert resposta.json()["avatar_url"] is None
    assert list(midia.iterdir()) == []


def test_remover_avatar_externo_nao_apaga_arquivo_nenhum(
    cliente: TestClient, autenticado: dict[str, str], db: Session, usuario: Usuario, midia: Path
) -> None:
    (midia / "intocado.webp").write_bytes(b"x")
    usuario.avatar_url = "https://avatars.githubusercontent.com/u/1"
    db.commit()

    cliente.delete("/api/v1/usuarios/me/avatar", headers=autenticado)

    assert (midia / "intocado.webp").exists()


def test_expurgo_da_conta_apaga_a_foto(
    cliente: TestClient, autenticado: dict[str, str], db: Session, usuario: Usuario, midia: Path
) -> None:
    _enviar(cliente, autenticado, _imagem())
    db.refresh(usuario)
    usuario.exclusao_agendada_para = datetime.now(UTC) - timedelta(days=1)
    db.commit()

    assert conta.expurgar_vencidas(db) == 1
    assert list(midia.iterdir()) == []


def test_avatar_exige_autenticacao(cliente: TestClient, midia: Path) -> None:
    resposta = cliente.put(
        "/api/v1/usuarios/me/avatar", files={"arquivo": ("f.png", _imagem(), "image/png")}
    )
    assert resposta.status_code == 401


# --------------------------------------------------------------------------
# Perfil público e autorização
# --------------------------------------------------------------------------


def test_perfil_publico_traz_so_o_que_o_ranking_mostra(
    cliente: TestClient, autenticado: dict[str, str], outro: Usuario, db: Session
) -> None:
    outro.xp_total = 260
    db.commit()

    resposta = cliente.get("/api/v1/usuarios/bia", headers=autenticado)

    assert resposta.status_code == 200
    assert resposta.json() == {
        "username": "bia",
        "nome_exibicao": "Bia Souza",
        "avatar_url": None,
        "nivel": 3,
        "xp_total": 260,
        "streak_dias": 0,
    }


def test_perfil_publico_ignora_maiusculas(
    cliente: TestClient, autenticado: dict[str, str], outro: Usuario
) -> None:
    assert cliente.get("/api/v1/usuarios/BIA", headers=autenticado).status_code == 200


def test_perfil_publico_nao_conta_acesso_no_streak_de_quem_e_visto(
    cliente: TestClient, autenticado: dict[str, str], outro: Usuario
) -> None:
    for _ in range(3):
        corpo = cliente.get("/api/v1/usuarios/bia", headers=autenticado).json()

    assert corpo["streak_dias"] == 0


def test_perfil_publico_de_quem_nao_existe_responde_404(
    cliente: TestClient, autenticado: dict[str, str]
) -> None:
    resposta = cliente.get("/api/v1/usuarios/ninguem", headers=autenticado)

    assert resposta.status_code == 404
    assert resposta.json()["erro"]["code"] == "usuario_nao_encontrado"


def test_perfil_publico_de_quem_pediu_exclusao_responde_404(
    cliente: TestClient, autenticado: dict[str, str], outro: Usuario, db: Session
) -> None:
    outro.exclusao_agendada_para = datetime.now(UTC) + timedelta(days=30)
    db.commit()

    assert cliente.get("/api/v1/usuarios/bia", headers=autenticado).status_code == 404


def test_perfil_publico_exige_autenticacao(cliente: TestClient, outro: Usuario) -> None:
    assert cliente.get("/api/v1/usuarios/bia").status_code == 401


def test_rota_me_nao_e_confundida_com_username(
    cliente: TestClient, autenticado: dict[str, str], usuario: Usuario
) -> None:
    assert cliente.get("/api/v1/usuarios/me", headers=autenticado).json()["email"] == usuario.email


@pytest.mark.parametrize(
    ("metodo", "corpo"),
    [
        ("patch", {"nome_exibicao": "Invasora"}),
        ("put", None),
        ("delete", {"confirmacao": "EXCLUIR", "senha": SENHA_VALIDA}),
    ],
)
def test_nao_existe_rota_para_alterar_o_perfil_de_outro_aluno(
    cliente: TestClient,
    autenticado: dict[str, str],
    outro: Usuario,
    db: Session,
    metodo: str,
    corpo: dict | None,
) -> None:
    """Só `/me` escreve. O username de outra pessoa no caminho não abre porta nenhuma."""
    resposta = cliente.request(metodo, "/api/v1/usuarios/bia", headers=autenticado, json=corpo)

    assert resposta.status_code == 405
    db.refresh(outro)
    assert outro.nome_exibicao == "Bia Souza"
    assert outro.exclusao_agendada_para is None


def test_escrever_no_proprio_perfil_nao_mexe_no_de_outro(
    cliente: TestClient, autenticado: dict[str, str], outro: Usuario, db: Session
) -> None:
    cliente.patch("/api/v1/usuarios/me", headers=autenticado, json={"nome_exibicao": "Ana L."})
    cliente.patch(
        "/api/v1/usuarios/me/preferencias", headers=autenticado, json={"alto_contraste": True}
    )
    cliente.patch("/api/v1/usuarios/me/trilha", headers=autenticado, json={"tipo_trilha": "livre"})

    db.refresh(outro)
    assert (outro.nome_exibicao, outro.alto_contraste, outro.tipo_trilha) == (
        "Bia Souza",
        False,
        TipoTrilha.guiada,
    )
