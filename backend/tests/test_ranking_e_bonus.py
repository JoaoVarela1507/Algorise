"""O que faltava da gamificação (#31): ranking por trilha, `/ranking/me`, desempate,
bônus da trilha concluída e o dia do streak no fuso do aluno."""

from datetime import UTC, date, datetime, timedelta

import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Atividade, Modulo, OrigemXP, TipoAtividade, Trilha, Usuario, XPEvento
from app.services import ranking, streak, xp
from app.services.submissoes import XP_POR_PASSO, XP_POR_TRILHA


@pytest.fixture(autouse=True)
def sem_redis_de_verdade(redis_falso: fakeredis.FakeRedis) -> None:
    """O ranking fala com o Redis a cada XP: aqui, o falso, na hora."""


def aluno(db: Session, nome: str, xp_total: int = 0, quando: datetime | None = None) -> Usuario:
    registro = Usuario(
        email=f"{nome}@ufrpe.br",
        username=nome,
        nome_exibicao=nome,
        xp_total=xp_total,
        xp_alcancado_em=quando,
    )
    db.add(registro)
    db.commit()
    return registro


@pytest.fixture
def python(db: Session) -> Trilha:
    trilha = Trilha(slug="py", nome="Python", disciplina="Algoritmos", publicada=True)
    trilha.modulos = [Modulo(ordem=1, titulo="Um"), Modulo(ordem=2, titulo="Dois")]
    trilha.modulos[0].atividades = [
        Atividade(
            ordem=1,
            tipo=TipoAtividade.terminal,
            enunciado="e",
            comando_esperado="ls",
            saida_esperada="a",
        )
    ]
    db.add(trilha)
    db.commit()
    return trilha


# --- desempate ----------------------------------------------------------------------------


def test_empate_de_xp_fica_na_frente_quem_chegou_antes(db: Session) -> None:
    agora = datetime.now(UTC)
    tarde = aluno(db, "tarde", 100, agora)
    cedo = aluno(db, "cedo", 100, agora - timedelta(days=2))
    aluno(db, "mais", 150, agora)

    pelo_banco = ranking.obter_ranking(db, limite=10, deslocamento=0)

    assert [e.username for e in pelo_banco.lista] == ["mais", "cedo", "tarde"]
    assert ranking.score_de(100, cedo.xp_alcancado_em) > ranking.score_de(
        100, tarde.xp_alcancado_em
    )
    assert int(ranking.score_de(100, agora)) == 100


def test_empate_tambem_no_redis(db: Session, redis_falso: fakeredis.FakeRedis) -> None:
    agora = datetime.now(UTC)
    aluno(db, "tarde", 100, agora)
    aluno(db, "cedo", 100, agora - timedelta(hours=3))

    pelo_redis = ranking.obter_ranking(db, limite=10, deslocamento=0)

    assert [(e.username, e.xp) for e in pelo_redis.lista] == [("cedo", 100), ("tarde", 100)]


def test_ganhar_xp_atualiza_o_score_e_a_data(db: Session, redis_falso: fakeredis.FakeRedis) -> None:
    ana = aluno(db, "ana")
    ranking.aquecer(db)

    xp.registrar_xp(db, usuario_id=ana.id, valor=30, origem=OrigemXP.atividade)

    db.expire_all()
    assert db.get(Usuario, ana.id).xp_alcancado_em is not None
    assert int(float(redis_falso.zscore(ranking.CHAVE_RANKING, str(ana.id)))) == 30


# --- rotas --------------------------------------------------------------------------------


def test_minha_posicao_e_o_ranking_geral(
    cliente: TestClient, autenticado: dict[str, str], db: Session, usuario: Usuario
) -> None:
    aluno(db, "lider", 500, datetime.now(UTC))

    me = cliente.get("/api/v1/ranking/me", headers=autenticado).json()
    geral = cliente.get("/api/v1/ranking/geral", headers=autenticado).json()

    assert (me["posicao"], me["usuario_id"]) == (2, usuario.id)
    assert geral["usuario"]["posicao"] == 2
    assert geral["podio"][0]["username"] == "lider"


def test_ranking_da_trilha_conta_so_o_xp_dela(
    cliente: TestClient, db: Session, python: Trilha
) -> None:
    ana, bia = aluno(db, "ana"), aluno(db, "bia")
    outra = Trilha(slug="sql", nome="SQL", disciplina="BD", publicada=True)
    outra.modulos = [Modulo(ordem=1, titulo="Select")]
    db.add(outra)
    db.commit()
    atividade = python.modulos[0].atividades[0]
    agora = datetime.now(UTC)
    db.add_all(
        [
            XPEvento(
                usuario_id=ana.id,
                origem=OrigemXP.atividade,
                referencia_id=atividade.id,
                valor=10,
                criado_em=agora,
            ),
            XPEvento(
                usuario_id=bia.id,
                origem=OrigemXP.modulo,
                referencia_id=python.modulos[0].id,
                valor=20,
                criado_em=agora,
            ),
            XPEvento(
                usuario_id=bia.id,
                origem=OrigemXP.trilha,
                referencia_id=python.id,
                valor=40,
                criado_em=agora,
            ),
            # XP de outra trilha não conta aqui.
            XPEvento(
                usuario_id=ana.id,
                origem=OrigemXP.modulo,
                referencia_id=outra.modulos[0].id,
                valor=999,
                criado_em=agora,
            ),
        ]
    )
    db.commit()

    corpo = cliente.get(f"/api/v1/ranking/trilhas/{python.id}").json()

    assert [(e["username"], e["xp"]) for e in corpo["lista"]] == [("bia", 60), ("ana", 10)]
    assert corpo["total"] == 2
    assert cliente.get("/api/v1/ranking/trilhas/9999").status_code == 404


# --- bônus da trilha ----------------------------------------------------------------------


def test_fechar_a_trilha_paga_o_bonus_uma_vez(
    cliente: TestClient, autenticado: dict[str, str], db: Session, usuario: Usuario
) -> None:
    trilha = Trilha(slug="curta", nome="Curta", disciplina="X", publicada=True)
    trilha.modulos = [Modulo(ordem=1, titulo="Único")]
    db.add(trilha)
    db.commit()

    primeira = cliente.post("/api/v1/trilhas/curta/passos/1/concluir", headers=autenticado).json()
    segunda = cliente.post("/api/v1/trilhas/curta/passos/1/concluir", headers=autenticado).json()

    assert primeira["xp_ganho"] == XP_POR_PASSO + XP_POR_TRILHA
    assert segunda["xp_ganho"] == 0
    bonus = db.scalars(
        select(XPEvento).where(
            XPEvento.usuario_id == usuario.id, XPEvento.origem == OrigemXP.trilha
        )
    ).all()
    assert len(bonus) == 1


# --- streak no fuso ----------------------------------------------------------------------


def test_dia_do_streak_e_o_do_fuso_configurado(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "fuso_horario", "Pacific/Kiritimati")  # UTC+14
    adiantado = streak.hoje_no_fuso()
    monkeypatch.setattr(settings, "fuso_horario", "Pacific/Pago_Pago")  # UTC-11
    atrasado = streak.hoje_no_fuso()

    # 25 horas de diferença: os dois dias nunca são o mesmo.
    assert adiantado - atrasado in (timedelta(days=1), timedelta(days=2))
    assert isinstance(adiantado, date)


def test_virada_do_dia_vem_do_fuso(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "fuso_horario", "America/Recife")
    hoje = streak.hoje_no_fuso()

    segundos = streak._segundos_ate_amanha(hoje)

    assert 1 <= segundos <= 24 * 60 * 60
