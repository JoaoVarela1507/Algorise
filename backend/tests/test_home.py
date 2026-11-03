"""Testes do que a home mostra além do ranking (tela 16): meta diária, conquistas e trilha atual."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    Atividade,
    Modulo,
    OrigemXP,
    RespostaUsuario,
    Streak,
    TipoAtividade,
    Trilha,
    Usuario,
)
from app.services import gamificacao, progresso, xp


@pytest.fixture
def trilha_com_passos(db: Session) -> Trilha:
    trilha = Trilha(slug="redes", nome="Redes", disciplina="Redes", periodo=3, publicada=True)
    for ordem, titulo in enumerate(["Modelo OSI", "TCP/IP", "DNS"], start=1):
        modulo = Modulo(ordem=ordem, titulo=titulo)
        modulo.atividades.append(
            Atividade(ordem=1, tipo=TipoAtividade.terminal, enunciado="Rode", xp=10)
        )
        trilha.modulos.append(modulo)
    db.add(trilha)
    db.commit()
    return trilha


def _responder(
    db: Session,
    usuario: Usuario,
    atividade: Atividade,
    *,
    correta: bool = True,
    segundos: int | None = None,
    quando: datetime | None = None,
) -> None:
    resposta = RespostaUsuario(
        usuario_id=usuario.id,
        atividade_id=atividade.id,
        conteudo="x",
        correta=correta,
        tempo_gasto_segundos=segundos,
    )
    if quando is not None:
        # Em UTC, como o banco grava: o SQLite dos testes descarta o fuso em vez
        # de converter.
        resposta.criado_em = quando.astimezone(UTC)
    db.add(resposta)
    db.commit()


def _conquistas(cliente: TestClient, autenticado: dict[str, str]) -> dict[str, bool]:
    corpo = cliente.get("/api/v1/gamificacao/conquistas", headers=autenticado).json()
    return {c["id"]: c["desbloqueada"] for c in corpo}


# --------------------------------------------------------------------------
# Meta diária
# --------------------------------------------------------------------------


def test_meta_comeca_zerada(cliente: TestClient, autenticado: dict[str, str]) -> None:
    corpo = cliente.get("/api/v1/gamificacao/meta-diaria", headers=autenticado).json()

    assert corpo == {
        "xp_hoje": 0,
        "xp_meta": settings.xp_meta_diaria,
        "desafios_resolvidos": 0,
        "minutos_estudados": 0,
    }


def test_meta_exige_autenticacao(cliente: TestClient) -> None:
    assert cliente.get("/api/v1/gamificacao/meta-diaria").status_code == 401


def test_meta_soma_o_que_o_aluno_fez_hoje(
    cliente: TestClient,
    db: Session,
    usuario: Usuario,
    autenticado: dict[str, str],
    trilha_com_passos: Trilha,
    redis_falso: fakeredis.FakeRedis,
) -> None:
    atividade = trilha_com_passos.modulos[0].atividades[0]
    outra = trilha_com_passos.modulos[1].atividades[0]
    # Errou, acertou e acertou outra: dois desafios, não três.
    _responder(db, usuario, atividade, correta=False, segundos=120)
    _responder(db, usuario, atividade, segundos=300)
    _responder(db, usuario, outra, segundos=90)
    xp.registrar_xp(db, usuario_id=usuario.id, valor=20, origem=OrigemXP.atividade)

    corpo = cliente.get("/api/v1/gamificacao/meta-diaria", headers=autenticado).json()

    assert corpo["xp_hoje"] == 20
    assert corpo["desafios_resolvidos"] == 2
    assert corpo["minutos_estudados"] == (120 + 300 + 90) // 60


def test_meta_ignora_o_que_foi_ontem(
    cliente: TestClient,
    db: Session,
    usuario: Usuario,
    autenticado: dict[str, str],
    trilha_com_passos: Trilha,
) -> None:
    inicio, _ = gamificacao.janela_do_dia()
    _responder(
        db,
        usuario,
        trilha_com_passos.modulos[0].atividades[0],
        segundos=600,
        quando=inicio - timedelta(minutes=1),
    )

    corpo = cliente.get("/api/v1/gamificacao/meta-diaria", headers=autenticado).json()

    assert corpo["desafios_resolvidos"] == 0
    assert corpo["minutos_estudados"] == 0


def test_o_dia_vira_no_fuso_do_aluno() -> None:
    """23h no Recife já é o dia seguinte em UTC, e ainda conta como hoje."""
    fuso = ZoneInfo(settings.fuso_horario)
    noite = datetime(2026, 3, 10, 23, 0, tzinfo=fuso)

    inicio, fim = gamificacao.janela_do_dia(noite)

    assert inicio == datetime(2026, 3, 10, tzinfo=fuso).astimezone(UTC)
    assert fim - inicio == timedelta(days=1)
    assert inicio <= noite.astimezone(UTC) < fim


# --------------------------------------------------------------------------
# Conquistas
# --------------------------------------------------------------------------


def test_aluno_novo_nao_tem_conquista(cliente: TestClient, autenticado: dict[str, str]) -> None:
    conquistas = _conquistas(cliente, autenticado)

    assert set(conquistas) == {
        "primeiro-passo",
        "em-chamas",
        "top-10",
        "coruja",
        "maratonista",
        "trilha-completa",
    }
    assert not any(conquistas.values())


def test_primeiro_acerto_desbloqueia_o_primeiro_passo(
    cliente: TestClient,
    db: Session,
    usuario: Usuario,
    autenticado: dict[str, str],
    trilha_com_passos: Trilha,
) -> None:
    atividade = trilha_com_passos.modulos[0].atividades[0]
    _responder(db, usuario, atividade, correta=False)
    assert not _conquistas(cliente, autenticado)["primeiro-passo"]

    _responder(db, usuario, atividade)
    assert _conquistas(cliente, autenticado)["primeiro-passo"]


def test_tres_dias_seguidos_acendem_em_chamas(
    cliente: TestClient, db: Session, usuario: Usuario, autenticado: dict[str, str]
) -> None:
    db.add(Streak(usuario_id=usuario.id, dias_consecutivos=0, maior_sequencia=3))
    db.commit()

    assert _conquistas(cliente, autenticado)["em-chamas"]


def test_top_10_exige_xp(
    cliente: TestClient,
    db: Session,
    usuario: Usuario,
    autenticado: dict[str, str],
    redis_falso: fakeredis.FakeRedis,
) -> None:
    # Sozinho e zerado, ele é o primeiro, mas de nada.
    assert not _conquistas(cliente, autenticado)["top-10"]

    xp.registrar_xp(db, usuario_id=usuario.id, valor=10, origem=OrigemXP.atividade)
    assert _conquistas(cliente, autenticado)["top-10"]


def test_coruja_e_acerto_de_madrugada(
    cliente: TestClient,
    db: Session,
    usuario: Usuario,
    autenticado: dict[str, str],
    trilha_com_passos: Trilha,
) -> None:
    fuso = ZoneInfo(settings.fuso_horario)
    atividade = trilha_com_passos.modulos[0].atividades[0]
    _responder(db, usuario, atividade, quando=datetime(2026, 3, 10, 22, 0, tzinfo=fuso))
    assert not _conquistas(cliente, autenticado)["coruja"]

    _responder(db, usuario, atividade, quando=datetime(2026, 3, 11, 1, 30, tzinfo=fuso))
    assert _conquistas(cliente, autenticado)["coruja"]


def test_maratonista_soma_o_tempo_de_um_dia_so(
    cliente: TestClient,
    db: Session,
    usuario: Usuario,
    autenticado: dict[str, str],
    trilha_com_passos: Trilha,
) -> None:
    fuso = ZoneInfo(settings.fuso_horario)
    atividade = trilha_com_passos.modulos[0].atividades[0]
    # 40 min num dia e 40 no outro: são 80, mas nenhum dia chegou a 60.
    _responder(
        db, usuario, atividade, segundos=40 * 60, quando=datetime(2026, 3, 10, 10, tzinfo=fuso)
    )
    _responder(
        db, usuario, atividade, segundos=40 * 60, quando=datetime(2026, 3, 11, 10, tzinfo=fuso)
    )
    assert not _conquistas(cliente, autenticado)["maratonista"]

    _responder(
        db, usuario, atividade, segundos=20 * 60, quando=datetime(2026, 3, 11, 15, tzinfo=fuso)
    )
    assert _conquistas(cliente, autenticado)["maratonista"]


def test_trilha_completa_exige_todos_os_passos(
    cliente: TestClient,
    db: Session,
    usuario: Usuario,
    autenticado: dict[str, str],
    trilha_com_passos: Trilha,
) -> None:
    *antes, ultimo = trilha_com_passos.modulos
    for modulo in antes:
        progresso.concluir_passo(db, usuario_id=usuario.id, trilha=trilha_com_passos, modulo=modulo)
    assert not _conquistas(cliente, autenticado)["trilha-completa"]

    progresso.concluir_passo(db, usuario_id=usuario.id, trilha=trilha_com_passos, modulo=ultimo)
    assert _conquistas(cliente, autenticado)["trilha-completa"]


# --------------------------------------------------------------------------
# Trilha atual
# --------------------------------------------------------------------------


def test_sem_trilha_publicada_e_null(cliente: TestClient, autenticado: dict[str, str]) -> None:
    resposta = cliente.get("/api/v1/trilhas/atual", headers=autenticado)

    assert resposta.status_code == 200
    assert resposta.json() is None


def test_trilha_atual_exige_autenticacao(cliente: TestClient) -> None:
    assert cliente.get("/api/v1/trilhas/atual").status_code == 401


def test_quem_nao_comecou_recebe_a_sugestao(
    cliente: TestClient, autenticado: dict[str, str], trilha_com_passos: Trilha
) -> None:
    corpo = cliente.get("/api/v1/trilhas/atual", headers=autenticado).json()

    assert corpo["slug"] == "redes"
    assert corpo["progresso"] == 0
    assert corpo["total_modulos"] == 3
    assert corpo["proximo_modulo"] == "Modelo OSI"


def test_trilha_atual_e_a_que_o_aluno_esta_fazendo(
    cliente: TestClient,
    db: Session,
    usuario: Usuario,
    autenticado: dict[str, str],
    trilha: Trilha,
    trilha_com_passos: Trilha,
) -> None:
    primeiro, segundo, _ = trilha_com_passos.modulos
    progresso.concluir_passo(db, usuario_id=usuario.id, trilha=trilha_com_passos, modulo=primeiro)

    corpo = cliente.get("/api/v1/trilhas/atual", headers=autenticado).json()

    assert corpo["slug"] == "redes"
    assert corpo["progresso"] == 1
    assert corpo["proximo_modulo"] == segundo.titulo


def test_trilha_terminada_deixa_de_ser_a_atual(
    cliente: TestClient,
    db: Session,
    usuario: Usuario,
    autenticado: dict[str, str],
    trilha_com_passos: Trilha,
) -> None:
    outra = Trilha(
        slug="so", nome="Sistemas Operacionais", disciplina="SO", periodo=3, publicada=True
    )
    outra.modulos.append(Modulo(ordem=1, titulo="Processos"))
    db.add(outra)
    db.commit()
    for modulo in trilha_com_passos.modulos:
        progresso.concluir_passo(db, usuario_id=usuario.id, trilha=trilha_com_passos, modulo=modulo)

    corpo = cliente.get("/api/v1/trilhas/atual", headers=autenticado).json()

    assert corpo["slug"] == "so"
    assert corpo["proximo_modulo"] == "Processos"
