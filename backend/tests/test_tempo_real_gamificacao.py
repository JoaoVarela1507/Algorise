"""Ranking, XP e notificações em tempo real (#37)."""

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from typing import Any

import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import WebSocketTestSession

from app.core.config import settings
from app.core.seguranca import criar_access_token
from app.models import (
    Atividade,
    Modulo,
    Notificacao,
    OrigemXP,
    Parceiro,
    ProgressoUsuario,
    StatusProgresso,
    Streak,
    TipoAtividade,
    Trilha,
    Usuario,
)
from app.services import certificados, notificacoes, ranking_ao_vivo, tempo_real, xp
from app.tarefas import streak_risco

URL_WS = "/api/v1/ws"


@pytest.fixture(autouse=True)
def tempo_real_limpo(redis_falso: fakeredis.FakeRedis) -> Iterator[None]:
    tempo_real.ouvinte.parar()
    ranking_ao_vivo.agregador.parar()
    ranking_ao_vivo._sujos_locais.clear()
    ranking_ao_vivo._fotos_locais.clear()
    yield
    tempo_real.ouvinte.parar()
    ranking_ao_vivo.agregador.parar()


def aluno(db: Session, nome: str) -> Usuario:
    registro = Usuario(email=f"{nome}@ufrpe.br", username=nome, nome_exibicao=nome.title())
    db.add(registro)
    db.commit()
    return registro


@pytest.fixture
def trilha(db: Session) -> Trilha:
    registro = Trilha(slug="py", nome="Python", disciplina="Algoritmos", publicada=True)
    registro.modulos = [Modulo(ordem=1, titulo="Laços")]
    registro.modulos[0].atividades = [
        Atividade(ordem=1, tipo=TipoAtividade.terminal, enunciado="e", comando_esperado="ls"),
        Atividade(ordem=2, tipo=TipoAtividade.terminal, enunciado="f", comando_esperado="pwd"),
    ]
    db.add(registro)
    db.commit()
    return registro


def entrar(cliente: TestClient, usuario: Usuario, *canais: str) -> WebSocketTestSession:
    ws = cliente.websocket_connect(URL_WS).__enter__()
    ws.send_json({"tipo": "autenticar", "token": criar_access_token(usuario.id)})
    assert ws.receive_json()["tipo"] == "autenticado"
    for canal in canais:
        ws.send_json({"tipo": "inscrever", "canal": canal})
        assert ws.receive_json()["tipo"] == "inscrito"
    return ws


def ate_o_evento(ws: WebSocketTestSession, nome: str) -> dict[str, Any]:
    while True:
        mensagem = ws.receive_json()
        if mensagem.get("evento") == nome:
            return mensagem


class Publicados:
    """Troca o `publicar` do ranking ao vivo por uma lista."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.eventos: list[tuple[str, str, dict[str, Any]]] = []
        monkeypatch.setattr(
            ranking_ao_vivo,
            "publicar",
            lambda canal, evento, payload=None: self.eventos.append((canal, evento, payload)),
        )


# --- xp.ganho e conquistas ----------------------------------------------------------------


def test_xp_ganho_chega_com_o_nivel(cliente: TestClient, db: Session, usuario: Usuario) -> None:
    ws = entrar(cliente, usuario, notificacoes.canal_de(usuario.id))
    try:
        xp.registrar_xp(db, usuario_id=usuario.id, valor=30, origem=OrigemXP.atividade)

        evento = ate_o_evento(ws, "xp.ganho")["payload"]
    finally:
        ws.__exit__(None, None, None)

    assert evento == {
        "valor": 30,
        "origem": "atividade",
        "xp_total": 30,
        "nivel": 1,
        "xp_no_nivel": 30,
        "xp_para_o_proximo": 20,
    }


def test_subir_de_nivel_e_uma_conquista_gravada(
    cliente: TestClient, db: Session, usuario: Usuario
) -> None:
    ws = entrar(cliente, usuario, notificacoes.canal_de(usuario.id))
    try:
        xp.registrar_xp(db, usuario_id=usuario.id, valor=60, origem=OrigemXP.atividade)

        evento = ate_o_evento(ws, notificacoes.CONQUISTA)["payload"]
    finally:
        ws.__exit__(None, None, None)

    assert evento["titulo"] == "Nível 2!"
    assert evento["dados"] == {"conquista": "nivel", "nivel": 2}
    gravada = db.scalars(select(Notificacao)).one()
    assert (gravada.tipo, gravada.lida_em) == (notificacoes.CONQUISTA, None)


def test_xp_sem_subir_de_nivel_nao_grava_conquista(db: Session, usuario: Usuario) -> None:
    xp.registrar_xp(db, usuario_id=usuario.id, valor=10, origem=OrigemXP.atividade)

    assert db.scalars(select(Notificacao)).all() == []


def test_certificado_emitido_vira_notificacao(db: Session, usuario: Usuario) -> None:
    trilha = Trilha(slug="parc", nome="Parceira", disciplina="X", publicada=True)
    trilha.parceiro = Parceiro(nome="UFRPE")
    trilha.modulos = [Modulo(ordem=1, titulo="Único")]
    db.add(trilha)
    db.commit()
    db.add(
        ProgressoUsuario(
            usuario_id=usuario.id,
            trilha_id=trilha.id,
            modulo_id=trilha.modulos[0].id,
            status=StatusProgresso.concluido,
            concluido_em=datetime.now(UTC),
        )
    )
    db.commit()

    certificado = certificados.emitir_se_concluiu(db, usuario, trilha)

    assert certificado is not None
    aviso = db.scalars(select(Notificacao)).one()
    assert aviso.tipo == notificacoes.CERTIFICADO
    assert aviso.dados == {"certificado_id": certificado.id, "trilha_id": trilha.id}


# --- streak em risco ----------------------------------------------------------------------


def test_streak_em_risco_avisa_uma_vez_so_quem_nao_entrou_hoje(db: Session) -> None:
    hoje = date(2026, 11, 3)
    em_risco, ja_entrou, perdido = aluno(db, "ana"), aluno(db, "bia"), aluno(db, "caio")
    db.add_all(
        [
            Streak(usuario_id=em_risco.id, dias_consecutivos=5, ultimo_acesso=hoje - timedelta(1)),
            Streak(usuario_id=ja_entrou.id, dias_consecutivos=2, ultimo_acesso=hoje),
            Streak(usuario_id=perdido.id, dias_consecutivos=0, ultimo_acesso=hoje - timedelta(3)),
        ]
    )
    db.commit()

    assert streak_risco.avisar(db, hoje=hoje) == 1
    assert streak_risco.avisar(db, hoje=hoje) == 0

    aviso = db.scalars(select(Notificacao)).one()
    assert (aviso.usuario_id, aviso.tipo) == (em_risco.id, notificacoes.STREAK_EM_RISCO)
    assert "5 dias" in aviso.mensagem


# --- centro de notificações ---------------------------------------------------------------


def test_centro_de_notificacoes(
    cliente: TestClient, autenticado: dict[str, str], db: Session, usuario: Usuario
) -> None:
    outro = aluno(db, "bia")
    for i in range(3):
        notificacoes.notificar(
            db, usuario.id, tipo=notificacoes.CONQUISTA, titulo=f"N{i}", mensagem="m"
        )
    alheia = notificacoes.notificar(
        db, outro.id, tipo=notificacoes.CONQUISTA, titulo="Dela", mensagem="m"
    )
    url = "/api/v1/notificacoes"

    lista = cliente.get(url, headers=autenticado).json()
    assert [n["titulo"] for n in lista["itens"]] == ["N2", "N1", "N0"]
    assert cliente.get(f"{url}/contagem", headers=autenticado).json() == {"nao_lidas": 3}

    primeira = lista["itens"][0]["id"]
    lida = cliente.post(f"{url}/{primeira}/lida", headers=autenticado).json()
    assert lida["lida_em"] is not None
    nao_lidas = cliente.get(f"{url}?nao_lidas=true", headers=autenticado).json()
    assert [n["titulo"] for n in nao_lidas["itens"]] == ["N1", "N0"]

    assert cliente.post(f"{url}/lidas", headers=autenticado).json() == {"marcadas": 2}
    assert cliente.get(f"{url}/contagem", headers=autenticado).json() == {"nao_lidas": 0}
    negada = cliente.post(f"{url}/{alheia.id}/lida", headers=autenticado)
    assert negada.status_code == 404
    assert cliente.get(url).status_code == 401


# --- ranking agregado e com delta ---------------------------------------------------------


def test_ranking_sai_agregado_num_evento_por_ranking(
    db: Session, trilha: Trilha, monkeypatch: pytest.MonkeyPatch
) -> None:
    publicados = Publicados(monkeypatch)
    ana = aluno(db, "ana")
    atividades = trilha.modulos[0].atividades
    for atividade in atividades:
        xp.registrar_xp(
            db, usuario_id=ana.id, valor=10, origem=OrigemXP.atividade, referencia_id=atividade.id
        )

    assert ranking_ao_vivo.descarregar(db) == 2
    assert sorted(canal for canal, _, _ in publicados.eventos) == sorted(
        ["ranking:geral", f"ranking:{trilha.id}"]
    )
    # Nada novo, nada publicado.
    assert ranking_ao_vivo.descarregar(db) == 0


def test_ranking_manda_so_quem_mudou(
    db: Session, trilha: Trilha, monkeypatch: pytest.MonkeyPatch
) -> None:
    publicados = Publicados(monkeypatch)
    ana, bia, caio = aluno(db, "ana"), aluno(db, "bia"), aluno(db, "caio")
    xp.registrar_xp(db, usuario_id=ana.id, valor=30, origem=OrigemXP.atividade)
    xp.registrar_xp(db, usuario_id=bia.id, valor=20, origem=OrigemXP.atividade)
    xp.registrar_xp(db, usuario_id=caio.id, valor=10, origem=OrigemXP.atividade)
    ranking_ao_vivo.descarregar(db)
    publicados.eventos.clear()

    # Caio passa Bia: os dois trocam de lugar, e Ana fica onde estava.
    xp.registrar_xp(db, usuario_id=caio.id, valor=15, origem=OrigemXP.atividade)
    ranking_ao_vivo.descarregar(db)

    [(canal, evento, payload)] = publicados.eventos
    assert (canal, evento) == ("ranking:geral", "ranking.atualizado")
    assert [(m["username"], m["posicao"], m["xp"]) for m in payload["mudancas"]] == [
        ("caio", 2, 25),
        ("bia", 3, 20),
    ]
    assert payload["total"] == 3


def test_sem_foto_anterior_manda_so_quem_ganhou(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    publicados = Publicados(monkeypatch)
    ana, bia = aluno(db, "ana"), aluno(db, "bia")
    xp.registrar_xp(db, usuario_id=ana.id, valor=30, origem=OrigemXP.atividade)
    ranking_ao_vivo._pegar_anotados()  # Ana já estava lá antes da foto existir.

    xp.registrar_xp(db, usuario_id=bia.id, valor=10, origem=OrigemXP.atividade)
    ranking_ao_vivo.descarregar(db)

    [(_, _, payload)] = publicados.eventos
    assert [m["username"] for m in payload["mudancas"]] == ["bia"]


def test_ranking_com_redis_fora_fica_na_memoria(
    db: Session, redis_fora: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    publicados = Publicados(monkeypatch)
    ana = aluno(db, "ana")
    xp.registrar_xp(db, usuario_id=ana.id, valor=30, origem=OrigemXP.atividade)

    assert ranking_ao_vivo.descarregar(db) == 1
    assert publicados.eventos[0][2]["mudancas"][0]["username"] == "ana"


def test_trilha_de_cada_origem(db: Session, trilha: Trilha) -> None:
    modulo = trilha.modulos[0]
    assert ranking_ao_vivo.trilha_de(db, OrigemXP.atividade, modulo.atividades[0].id) == trilha.id
    assert ranking_ao_vivo.trilha_de(db, OrigemXP.modulo, modulo.id) == trilha.id
    assert ranking_ao_vivo.trilha_de(db, OrigemXP.trilha, trilha.id) == trilha.id
    assert ranking_ao_vivo.trilha_de(db, OrigemXP.atividade, None) is None


def test_aceite_duas_contas_na_trilha_veem_a_posicao_mudar(
    cliente: TestClient, db: Session, trilha: Trilha, monkeypatch: pytest.MonkeyPatch
) -> None:
    """O critério de aceite: concluir uma atividade numa conta move a posição na outra.

    A descarga do ranking roda aqui, na thread do teste. A do agregador fica
    parada (intervalo de uma hora): o SQLite dos testes é uma conexão só, e a
    thread dele consultando enquanto o teste grava derrubava o socket às vezes.
    O agregador subindo e parando tem o teste dele.
    """
    monkeypatch.setattr(settings, "ranking_intervalo_ao_vivo", 3600)
    ana, bia = aluno(db, "ana"), aluno(db, "bia")
    canal = ranking_ao_vivo.canal_da_trilha(trilha.id)
    atividade = trilha.modulos[0].atividades[0]
    xp.registrar_xp(
        db, usuario_id=bia.id, valor=5, origem=OrigemXP.atividade, referencia_id=atividade.id
    )
    ws_bia = entrar(cliente, bia, canal)
    try:
        # A primeira descarga (de Bia) tira a foto.
        ranking_ao_vivo.descarregar(db)
        assert ate_o_evento(ws_bia, "ranking.atualizado")

        xp.registrar_xp(
            db,
            usuario_id=ana.id,
            valor=20,
            origem=OrigemXP.atividade,
            referencia_id=trilha.modulos[0].atividades[1].id,
        )
        ranking_ao_vivo.descarregar(db)
        evento = ate_o_evento(ws_bia, "ranking.atualizado")["payload"]
    finally:
        ws_bia.__exit__(None, None, None)

    assert [(m["username"], m["posicao"]) for m in evento["mudancas"]] == [
        ("ana", 1),
        ("bia", 2),
    ]


def test_agregador_sobe_uma_vez_e_para(sessao_factory: sessionmaker[Session]) -> None:
    ranking_ao_vivo.agregador.garantir(sessao_factory)
    thread = ranking_ao_vivo.agregador._thread
    ranking_ao_vivo.agregador.garantir(sessao_factory)

    assert ranking_ao_vivo.agregador._thread is thread
    ranking_ao_vivo.agregador.parar()
    assert thread is not None and not thread.is_alive()
