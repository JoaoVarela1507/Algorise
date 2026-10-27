"""Testes das regras de trilha, ranking, XP e streak.

O que se repete aqui é a pergunta "e se o Redis estiver fora?". Cada um desses
serviços responde isso de um jeito, e é justamente o que a #12 pede: cache e
ranking caem para o banco, sessão falha fechado.
"""

from datetime import date, timedelta

import fakeredis
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import OrigemXP, Trilha, Usuario, XPEvento
from app.services import ranking, streak, trilhas, xp


def criar_alunos(db: Session, xp_por_username: dict[str, int]) -> dict[str, Usuario]:
    alunos = {}
    for username, total in xp_por_username.items():
        aluno = Usuario(
            email=f"{username}@ufrpe.br",
            username=username,
            nome_exibicao=username.title(),
            xp_total=total,
        )
        db.add(aluno)
        alunos[username] = aluno
    db.commit()
    return alunos


# --------------------------------------------------------------------------
# Trilhas
# --------------------------------------------------------------------------


def test_detalhe_traz_modulos_e_total(cliente: TestClient, trilha: Trilha) -> None:
    resposta = cliente.get(f"/api/v1/trilhas/{trilha.slug}")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["slug"] == trilha.slug
    assert corpo["total_modulos"] == len(corpo["modulos"])


def test_catalogo_e_servido_do_cache_na_segunda_chamada(
    cliente: TestClient, trilha: Trilha, redis_falso: fakeredis.FakeRedis
) -> None:
    primeira = cliente.get("/api/v1/trilhas").json()
    chaves = redis_falso.keys("*catalogo*")

    segunda = cliente.get("/api/v1/trilhas").json()

    assert chaves, "a primeira chamada precisa deixar a página em cache"
    assert primeira == segunda


def test_cada_pagina_tem_sua_chave_de_cache(
    cliente: TestClient, trilha: Trilha, redis_falso: fakeredis.FakeRedis
) -> None:
    """Duas páginas são dois conteúdos: com a mesma chave, a 2 devolveria a 1."""
    cliente.get("/api/v1/trilhas", params={"tamanho_pagina": 1, "pagina": 1})
    cliente.get("/api/v1/trilhas", params={"tamanho_pagina": 1, "pagina": 2})

    assert len(redis_falso.keys("*catalogo*")) == 2


def test_invalidar_catalogo_limpa_o_prefixo(
    cliente: TestClient, trilha: Trilha, redis_falso: fakeredis.FakeRedis
) -> None:
    cliente.get("/api/v1/trilhas")

    assert trilhas.invalidar_catalogo() >= 1
    assert not redis_falso.keys("*catalogo*")


def test_catalogo_responde_com_redis_fora(
    cliente: TestClient, trilha: Trilha, redis_fora: None
) -> None:
    resposta = cliente.get("/api/v1/trilhas")

    assert resposta.status_code == 200
    assert resposta.json()["total"] == 1


# --------------------------------------------------------------------------
# Ranking
# --------------------------------------------------------------------------


def test_ranking_ordena_por_xp(db: Session, redis_falso: fakeredis.FakeRedis) -> None:
    criar_alunos(db, {"ana": 500, "bia": 300, "caio": 900})

    resultado = ranking.obter_ranking(db, limite=3)

    assert [entrada.username for entrada in resultado.podio] == ["caio", "ana", "bia"]
    assert [entrada.posicao for entrada in resultado.podio] == [1, 2, 3]
    assert resultado.total == 3


def test_ranking_aquece_o_sorted_set_do_banco(
    db: Session, redis_falso: fakeredis.FakeRedis
) -> None:
    criar_alunos(db, {"ana": 10})

    ranking.obter_ranking(db, limite=1)

    assert redis_falso.exists(ranking.CHAVE_RANKING)


def test_ganhar_xp_muda_a_posicao_na_hora(db: Session, redis_falso: fakeredis.FakeRedis) -> None:
    """A invalidação é explícita: quem grava XP corrige o score (#12)."""
    alunos = criar_alunos(db, {"ana": 500, "bia": 300, "caio": 600})
    ranking.obter_ranking(db, limite=3)

    # 400 cabe no teto por janela (#31); o que se testa aqui é o ranking.
    xp.registrar_xp(db, usuario_id=alunos["bia"].id, valor=400, origem=OrigemXP.atividade)

    assert ranking.obter_ranking(db, limite=3).podio[0].username == "bia"


def test_registrar_xp_grava_evento_e_saldo(db: Session, redis_falso: fakeredis.FakeRedis) -> None:
    """`xp_eventos` é a fonte da verdade; `usuarios.xp_total` é o cache dela."""
    alunos = criar_alunos(db, {"ana": 100})

    saldo = xp.registrar_xp(
        db, usuario_id=alunos["ana"].id, valor=50, origem=OrigemXP.atividade, referencia_id=7
    )

    assert saldo == 150
    evento = db.query(XPEvento).one()
    assert (evento.valor, evento.referencia_id) == (50, 7)


def test_ranking_pagina_continua_a_numeracao(db: Session, redis_falso: fakeredis.FakeRedis) -> None:
    criar_alunos(db, {"ana": 500, "bia": 300, "caio": 900, "davi": 100, "eva": 700})

    segunda = ranking.obter_ranking(db, limite=2, deslocamento=3)

    assert [entrada.posicao for entrada in segunda.lista] == [4, 5]
    assert [entrada.username for entrada in segunda.lista] == ["bia", "davi"]


def test_ranking_informa_a_posicao_do_aluno(db: Session, redis_falso: fakeredis.FakeRedis) -> None:
    """A tela 16 mostra a posição dele mesmo quando ela cai na página 40."""
    alunos = criar_alunos(db, {"ana": 500, "bia": 300, "caio": 900})

    resultado = ranking.obter_ranking(db, limite=1, usuario_id=alunos["bia"].id)

    assert resultado.usuario is not None
    assert (resultado.usuario.username, resultado.usuario.posicao) == ("bia", 3)


def test_ranking_cai_no_banco_com_redis_fora(db: Session, redis_fora: None) -> None:
    criar_alunos(db, {"ana": 500, "bia": 300, "caio": 900})

    resultado = ranking.obter_ranking(db, limite=3, usuario_id=1)

    assert [entrada.username for entrada in resultado.podio] == ["caio", "ana", "bia"]
    assert resultado.total == 3


def test_invalidar_ranking_forca_reconstrucao(
    db: Session, redis_falso: fakeredis.FakeRedis
) -> None:
    criar_alunos(db, {"ana": 500, "caio": 900})
    ranking.obter_ranking(db, limite=2)

    ranking.invalidar()

    assert not redis_falso.exists(ranking.CHAVE_RANKING)
    assert ranking.obter_ranking(db, limite=2).podio[0].username == "caio"


# --------------------------------------------------------------------------
# Streak
# --------------------------------------------------------------------------


def test_primeiro_acesso_conta_um_dia(
    db: Session, usuario: Usuario, redis_falso: fakeredis.FakeRedis
) -> None:
    resultado = streak.registrar_acesso(db, usuario.id, hoje=date(2026, 9, 30))

    assert resultado.dias_consecutivos == 1


def test_dois_acessos_no_mesmo_dia_nao_incrementam(
    db: Session, usuario: Usuario, redis_falso: fakeredis.FakeRedis
) -> None:
    hoje = date(2026, 9, 30)
    streak.registrar_acesso(db, usuario.id, hoje=hoje)

    resultado = streak.registrar_acesso(db, usuario.id, hoje=hoje)

    assert resultado.dias_consecutivos == 1
    assert len(redis_falso.keys("*streak*")) == 1


def test_marcador_do_streak_expira_na_virada_do_dia(
    db: Session, usuario: Usuario, redis_falso: fakeredis.FakeRedis
) -> None:
    """O streak é por dia de calendário, não por intervalo de 24 horas."""
    streak.registrar_acesso(db, usuario.id, hoje=date.today())

    marcador = redis_falso.keys("*streak*")[0]
    assert 0 < redis_falso.ttl(marcador) <= 86400


def test_dias_seguidos_incrementam_a_sequencia(
    db: Session, usuario: Usuario, redis_falso: fakeredis.FakeRedis
) -> None:
    hoje = date(2026, 9, 30)
    streak.registrar_acesso(db, usuario.id, hoje=hoje)

    resultado = streak.registrar_acesso(db, usuario.id, hoje=hoje + timedelta(days=1))

    assert resultado.dias_consecutivos == 2


def test_buraco_reinicia_a_sequencia_e_guarda_o_recorde(
    db: Session, usuario: Usuario, redis_falso: fakeredis.FakeRedis
) -> None:
    hoje = date(2026, 9, 30)
    streak.registrar_acesso(db, usuario.id, hoje=hoje)
    streak.registrar_acesso(db, usuario.id, hoje=hoje + timedelta(days=1))

    resultado = streak.registrar_acesso(db, usuario.id, hoje=hoje + timedelta(days=5))

    assert resultado.dias_consecutivos == 1
    assert resultado.maior_sequencia == 2


def test_leitura_zera_streak_vencido(
    db: Session, usuario: Usuario, redis_falso: fakeredis.FakeRedis
) -> None:
    """Mostrar o número velho seria mentir para o aluno."""
    hoje = date(2026, 9, 30)
    streak.registrar_acesso(db, usuario.id, hoje=hoje)

    resultado = streak.obter_streak(db, usuario.id, hoje=hoje + timedelta(days=30))

    assert resultado.dias_consecutivos == 0


def test_streak_funciona_com_redis_fora(db: Session, usuario: Usuario, redis_fora: None) -> None:
    """Sem o marcador diário, a conta é a mesma — só passa no banco toda vez."""
    hoje = date(2026, 9, 30)

    streak.registrar_acesso(db, usuario.id, hoje=hoje)
    resultado = streak.registrar_acesso(db, usuario.id, hoje=hoje + timedelta(days=1))

    assert resultado.dias_consecutivos == 2
