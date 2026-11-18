"""Testes de níveis, streak e teto de XP (#31)."""

from datetime import timedelta

import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models import OrigemXP, Streak, Usuario
from app.services import gamificacao, niveis, streak, xp

# --------------------------------------------------------------------------
# Curva de níveis
# --------------------------------------------------------------------------


def test_comeca_no_nivel_1() -> None:
    assert niveis.nivel_de(0) == 1
    assert niveis.nivel_de(niveis.BASE - 1) == 1


def test_o_primeiro_degrau_e_a_base() -> None:
    assert niveis.nivel_de(niveis.BASE) == 2


@pytest.mark.parametrize("nivel", range(1, 41))
def test_as_duas_funcoes_sao_inversas(nivel: int) -> None:
    """Se um dia alguém mexer na curva, as duas precisam continuar casando."""
    assert niveis.nivel_de(niveis.xp_do_nivel(nivel)) == nivel


def test_os_degraus_crescem() -> None:
    """Começo rápido, fim que não se alcança numa tarde."""
    degraus = [niveis.xp_do_nivel(nivel + 1) - niveis.xp_do_nivel(nivel) for nivel in range(1, 10)]

    assert degraus == sorted(degraus)
    assert degraus[0] < degraus[-1]


def test_faixa_fecha_a_conta() -> None:
    nivel, no_nivel, falta = niveis.faixa_do_nivel(1000)

    assert niveis.xp_do_nivel(nivel) + no_nivel == 1000
    assert 1000 + falta == niveis.xp_do_nivel(nivel + 1)


def test_xp_negativo_nao_quebra() -> None:
    assert niveis.nivel_de(-10) == 1


# --------------------------------------------------------------------------
# Painel
# --------------------------------------------------------------------------


def test_painel_traz_xp_nivel_e_streak(cliente: TestClient, autenticado: dict[str, str]) -> None:
    corpo = cliente.get("/api/v1/gamificacao/me", headers=autenticado).json()

    assert corpo["xp_total"] == 0
    assert corpo["nivel"] == 1
    assert corpo["xp_para_o_proximo"] == niveis.BASE
    assert corpo["streak_dias"] == 0


def test_painel_exige_autenticacao(cliente: TestClient) -> None:
    assert cliente.get("/api/v1/gamificacao/me").status_code == 401


def test_painel_acompanha_o_xp(
    cliente: TestClient,
    db: Session,
    usuario: Usuario,
    autenticado: dict[str, str],
    redis_falso: fakeredis.FakeRedis,
) -> None:
    xp.registrar_xp(db, usuario_id=usuario.id, valor=niveis.BASE, origem=OrigemXP.atividade)

    corpo = cliente.get("/api/v1/gamificacao/me", headers=autenticado).json()

    assert corpo["xp_total"] == niveis.BASE
    assert corpo["nivel"] == 2
    assert corpo["xp_no_nivel"] == 0


def test_painel_nao_mexe_no_streak(
    cliente: TestClient, db: Session, usuario: Usuario, autenticado: dict[str, str]
) -> None:
    """Uma tela que só exibe não deveria alterar a sequência do aluno."""
    cliente.get("/api/v1/gamificacao/me", headers=autenticado)

    assert streak.obter_streak(db, usuario.id).dias_consecutivos == 0


# --------------------------------------------------------------------------
# Check-in
# --------------------------------------------------------------------------


def test_checkin_comeca_a_sequencia(cliente: TestClient, autenticado: dict[str, str]) -> None:
    corpo = cliente.post("/api/v1/gamificacao/checkin", headers=autenticado).json()

    assert corpo["streak_dias"] == 1
    assert corpo["maior_streak"] == 1


def test_dois_checkins_no_mesmo_dia_contam_uma_vez(
    cliente: TestClient, autenticado: dict[str, str]
) -> None:
    cliente.post("/api/v1/gamificacao/checkin", headers=autenticado)

    corpo = cliente.post("/api/v1/gamificacao/checkin", headers=autenticado).json()

    assert corpo["streak_dias"] == 1


def test_dia_seguinte_incrementa(
    cliente: TestClient,
    db: Session,
    usuario: Usuario,
    autenticado: dict[str, str],
    redis_falso: fakeredis.FakeRedis,
) -> None:
    streak.registrar_acesso(db, usuario.id, hoje=streak.hoje_no_fuso() - timedelta(days=1))

    corpo = cliente.post("/api/v1/gamificacao/checkin", headers=autenticado).json()

    assert corpo["streak_dias"] == 2


def test_buraco_zera_mas_guarda_o_recorde(
    cliente: TestClient,
    db: Session,
    usuario: Usuario,
    autenticado: dict[str, str],
    redis_falso: fakeredis.FakeRedis,
) -> None:
    hoje = streak.hoje_no_fuso()
    streak.registrar_acesso(db, usuario.id, hoje=hoje - timedelta(days=10))
    streak.registrar_acesso(db, usuario.id, hoje=hoje - timedelta(days=9))

    corpo = cliente.post("/api/v1/gamificacao/checkin", headers=autenticado).json()

    assert corpo["streak_dias"] == 1
    assert corpo["maior_streak"] == 2


def test_checkin_exige_autenticacao(cliente: TestClient) -> None:
    assert cliente.post("/api/v1/gamificacao/checkin").status_code == 401


# --------------------------------------------------------------------------
# Teto de XP por janela
# --------------------------------------------------------------------------


def test_xp_normal_passa_pelo_teto(redis_falso: fakeredis.FakeRedis) -> None:
    assert gamificacao.xp_permitido(1, 20) == 20


def test_teto_corta_no_limite(redis_falso: fakeredis.FakeRedis) -> None:
    """O último ganho não é perdido inteiro: quem está a 5 do teto recebe 5."""
    gamificacao.xp_permitido(1, settings.xp_maximo_por_janela - 5)

    assert gamificacao.xp_permitido(1, 30) == 5
    assert gamificacao.xp_permitido(1, 30) == 0


def test_o_teto_e_por_aluno(redis_falso: fakeredis.FakeRedis) -> None:
    gamificacao.xp_permitido(1, settings.xp_maximo_por_janela)

    assert gamificacao.xp_permitido(2, 20) == 20


def test_teto_libera_tudo_com_redis_fora(redis_fora: None) -> None:
    """Derrubar a concessão por causa do cache puniria o aluno honesto (#12)."""
    assert gamificacao.xp_permitido(1, 999) == 999


def test_estourar_o_teto_nao_apaga_o_progresso(
    db: Session, usuario: Usuario, redis_falso: fakeredis.FakeRedis
) -> None:
    """A atividade continua feita; só não vira ponto."""
    xp.registrar_xp(
        db, usuario_id=usuario.id, valor=settings.xp_maximo_por_janela, origem=OrigemXP.atividade
    )

    saldo = xp.registrar_xp(db, usuario_id=usuario.id, valor=50, origem=OrigemXP.atividade)

    assert saldo == settings.xp_maximo_por_janela


def test_a_janela_tem_prazo(redis_falso: fakeredis.FakeRedis) -> None:
    gamificacao.xp_permitido(1, 10)

    chave = next(iter(redis_falso.keys("*xp:janela*")))
    assert 0 < redis_falso.ttl(chave) <= settings.xp_janela_segundos


# --------------------------------------------------------------------------
# Leitura sem efeito e primeiro acesso concorrente
# --------------------------------------------------------------------------


def test_painel_nao_cria_a_linha_do_streak(
    cliente: TestClient, db: Session, usuario: Usuario, autenticado: dict[str, str]
) -> None:
    """GET não escreve: a linha nasce no check-in, não na leitura."""
    corpo = cliente.get("/api/v1/gamificacao/me", headers=autenticado).json()

    assert (corpo["streak_dias"], corpo["maior_streak"]) == (0, 0)
    assert db.scalar(select(func.count()).select_from(Streak)) == 0


def test_leitura_mostra_zero_sem_gravar_o_zero(
    cliente: TestClient, db: Session, usuario: Usuario, autenticado: dict[str, str]
) -> None:
    db.add(
        Streak(
            usuario_id=usuario.id,
            dias_consecutivos=5,
            maior_sequencia=5,
            ultimo_acesso=streak.hoje_no_fuso() - timedelta(days=10),
        )
    )
    db.commit()

    corpo = cliente.get("/api/v1/gamificacao/me", headers=autenticado).json()

    assert (corpo["streak_dias"], corpo["maior_streak"]) == (0, 5)
    db.expire_all()
    assert db.scalar(select(Streak.dias_consecutivos)) == 5


def test_checkin_depois_da_leitura_de_sequencia_quebrada_recomeca_em_um(
    cliente: TestClient, db: Session, usuario: Usuario, autenticado: dict[str, str]
) -> None:
    """O zero não gravado não muda a conta: ela decide por `ultimo_acesso`."""
    db.add(
        Streak(
            usuario_id=usuario.id,
            dias_consecutivos=5,
            maior_sequencia=5,
            ultimo_acesso=streak.hoje_no_fuso() - timedelta(days=10),
        )
    )
    db.commit()
    cliente.get("/api/v1/gamificacao/me", headers=autenticado)

    corpo = cliente.post("/api/v1/gamificacao/checkin", headers=autenticado).json()

    assert (corpo["streak_dias"], corpo["maior_streak"]) == (1, 5)


def test_primeiro_acesso_concorrente_nao_estoura(
    db: Session,
    usuario: Usuario,
    sessao_factory: sessionmaker[Session],
    redis_falso: fakeredis.FakeRedis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /me e POST /checkin chegam juntos no primeiro acesso.

    Simula o request concorrente gravando a linha entre o select (que não achou
    nada) e o insert deste: antes do upsert, isso era `IntegrityError` e 500.
    """
    insercao_original = streak.insercao_idempotente

    def outro_request_ganha_a_corrida(dialeto: str, usuario_id: int):
        with sessao_factory() as outra:
            outra.add(Streak(usuario_id=usuario_id, dias_consecutivos=0, maior_sequencia=0))
            outra.commit()
        return insercao_original(dialeto, usuario_id)

    monkeypatch.setattr(streak, "insercao_idempotente", outro_request_ganha_a_corrida)

    resultado = streak.registrar_acesso(db, usuario.id)

    assert resultado.dias_consecutivos == 1
    assert db.scalar(select(func.count()).select_from(Streak)) == 1


def test_insercao_do_streak_no_postgres_ignora_o_conflito() -> None:
    sql = str(streak.insercao_idempotente("postgresql", 1).compile(dialect=postgresql.dialect()))

    assert "ON CONFLICT (usuario_id) DO NOTHING" in sql
