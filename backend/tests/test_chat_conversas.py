"""Parte REST do chat (#33): histórico, busca, arquivamento, grupos e sugestões."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Conversa,
    GrupoChat,
    MensagemChat,
    Modulo,
    PapelMensagem,
    ProgressoUsuario,
    StatusProgresso,
    Trilha,
    Usuario,
)

URL = "/api/v1/chat"


def conversa(
    db: Session, dono: Usuario, titulo: str, *falas: str, idade: timedelta = timedelta()
) -> Conversa:
    registro = Conversa(usuario_id=dono.id, titulo=titulo, atualizado_em=datetime.now(UTC) - idade)
    registro.mensagens = [
        MensagemChat(
            papel=PapelMensagem.usuario if i % 2 == 0 else PapelMensagem.assistente, conteudo=fala
        )
        for i, fala in enumerate(falas)
    ]
    db.add(registro)
    db.commit()
    return registro


@pytest.fixture
def outro(db: Session) -> Usuario:
    registro = Usuario(email="bia@ufrpe.br", username="bia", nome_exibicao="Bia")
    db.add(registro)
    db.commit()
    return registro


# --- conversas ----------------------------------------------------------------------------


def test_cria_conversa_com_titulo_da_primeira_mensagem(
    cliente: TestClient, autenticado: dict[str, str]
) -> None:
    com_mensagem = cliente.post(
        f"{URL}/conversas",
        json={"primeira_mensagem": "Como funciona um laço for?\nE o while?"},
        headers=autenticado,
    )
    vazia = cliente.post(f"{URL}/conversas", json={}, headers=autenticado)

    assert com_mensagem.status_code == 201
    assert com_mensagem.json()["titulo"] == "Como funciona um laço for?"
    assert vazia.json()["titulo"] == "Nova conversa"
    assert vazia.json()["arquivada"] is False


def test_historico_paginado_da_mais_recente_e_so_do_aluno(
    cliente: TestClient, autenticado: dict[str, str], db: Session, usuario: Usuario, outro: Usuario
) -> None:
    conversa(db, usuario, "Antiga", idade=timedelta(days=3))
    conversa(db, usuario, "Recente")
    conversa(db, usuario, "Meio", idade=timedelta(days=1))
    conversa(db, outro, "Da Bia")

    corpo = cliente.get(f"{URL}/conversas?tamanho_pagina=2", headers=autenticado).json()
    segunda = cliente.get(f"{URL}/conversas?tamanho_pagina=2&pagina=2", headers=autenticado).json()

    assert [c["titulo"] for c in corpo["itens"]] == ["Recente", "Meio"]
    assert [c["titulo"] for c in segunda["itens"]] == ["Antiga"]
    assert corpo["total"] == 3


def test_busca_no_titulo_e_no_conteudo(
    cliente: TestClient, autenticado: dict[str, str], db: Session, usuario: Usuario
) -> None:
    conversa(db, usuario, "Recursão", "O que é recursão?", "Uma função que chama a si mesma.")
    conversa(
        db, usuario, "Listas", "Como ordenar uma lista?", "Use sorted ou a recursão do quicksort."
    )
    conversa(db, usuario, "Strings", "Como juntar strings?")

    def buscar(termo: str) -> list[str]:
        resposta = cliente.get(f"{URL}/conversas", params={"busca": termo}, headers=autenticado)
        return sorted(c["titulo"] for c in resposta.json()["itens"])

    assert buscar("recursão") == ["Listas", "Recursão"]
    assert buscar("juntar") == ["Strings"]
    assert buscar("ponteiro") == []


def test_mensagens_da_conversa_na_ordem(
    cliente: TestClient, autenticado: dict[str, str], db: Session, usuario: Usuario, outro: Usuario
) -> None:
    minha = conversa(db, usuario, "Laços", "um", "dois", "três")
    alheia = conversa(db, outro, "Da Bia", "oi")

    corpo = cliente.get(
        f"{URL}/conversas/{minha.id}/mensagens?tamanho_pagina=2", headers=autenticado
    ).json()
    negada = cliente.get(f"{URL}/conversas/{alheia.id}/mensagens", headers=autenticado)

    assert [(m["papel"], m["conteudo"]) for m in corpo["itens"]] == [
        ("usuario", "um"),
        ("assistente", "dois"),
    ]
    assert corpo["total"] == 3
    assert negada.status_code == 404
    assert negada.json()["erro"]["code"] == "conversa_nao_encontrada"


def test_renomeia_e_arquiva(
    cliente: TestClient, autenticado: dict[str, str], db: Session, usuario: Usuario
) -> None:
    registro = conversa(db, usuario, "Velho")

    editada = cliente.patch(
        f"{URL}/conversas/{registro.id}",
        json={"titulo": "  Novo  ", "arquivada": True},
        headers=autenticado,
    ).json()
    ativas = cliente.get(f"{URL}/conversas", headers=autenticado).json()
    arquivadas = cliente.get(f"{URL}/conversas?arquivadas=true", headers=autenticado).json()

    assert (editada["titulo"], editada["arquivada"]) == ("Novo", True)
    assert ativas["itens"] == []
    assert [c["id"] for c in arquivadas["itens"]] == [registro.id]


def test_titulo_vazio_e_recusado(
    cliente: TestClient, autenticado: dict[str, str], db: Session, usuario: Usuario
) -> None:
    registro = conversa(db, usuario, "Algo")

    resposta = cliente.patch(
        f"{URL}/conversas/{registro.id}", json={"titulo": "   "}, headers=autenticado
    )

    assert resposta.status_code == 422


def test_apaga_a_conversa_com_as_mensagens(
    cliente: TestClient, autenticado: dict[str, str], db: Session, usuario: Usuario, outro: Usuario
) -> None:
    minha = conversa(db, usuario, "Sai", "a", "b").id
    alheia = conversa(db, outro, "Fica").id

    assert cliente.delete(f"{URL}/conversas/{minha}", headers=autenticado).status_code == 204
    assert cliente.delete(f"{URL}/conversas/{alheia}", headers=autenticado).status_code == 404

    db.expire_all()
    assert db.get(Conversa, minha) is None
    assert db.scalars(select(MensagemChat).where(MensagemChat.conversa_id == minha)).all() == []
    assert db.get(Conversa, alheia) is not None


def test_rotas_exigem_login(cliente: TestClient) -> None:
    assert cliente.get(f"{URL}/conversas").status_code == 401
    assert cliente.get(f"{URL}/grupos").status_code == 401


# --- grupos -------------------------------------------------------------------------------


def test_grupo_com_conversas_e_filtro_por_grupo(
    cliente: TestClient, autenticado: dict[str, str], db: Session, usuario: Usuario
) -> None:
    a, b = conversa(db, usuario, "A"), conversa(db, usuario, "B")
    conversa(db, usuario, "Fora")

    grupo = cliente.post(
        f"{URL}/grupos",
        json={"nome": "Prova 1", "conversa_ids": [a.id, b.id, a.id]},
        headers=autenticado,
    )
    filtradas = cliente.get(
        f"{URL}/conversas", params={"grupo_id": grupo.json()["id"]}, headers=autenticado
    ).json()

    assert grupo.status_code == 201
    assert sorted(c["titulo"] for c in grupo.json()["conversas"]) == ["A", "B"]
    assert sorted(c["titulo"] for c in filtradas["itens"]) == ["A", "B"]


def test_editar_grupo_troca_a_lista_inteira(
    cliente: TestClient, autenticado: dict[str, str], db: Session, usuario: Usuario
) -> None:
    a, b, c = (conversa(db, usuario, t) for t in "ABC")
    grupo = cliente.post(
        f"{URL}/grupos", json={"nome": "G", "conversa_ids": [a.id, b.id]}, headers=autenticado
    ).json()

    editado = cliente.patch(
        f"{URL}/grupos/{grupo['id']}",
        json={"nome": "Grupo", "conversa_ids": [b.id, c.id]},
        headers=autenticado,
    ).json()

    assert editado["nome"] == "Grupo"
    assert sorted(x["titulo"] for x in editado["conversas"]) == ["B", "C"]
    db.expire_all()
    assert db.get(Conversa, a.id).grupo_id is None


def test_conversa_muda_de_grupo_pelo_patch(
    cliente: TestClient, autenticado: dict[str, str], db: Session, usuario: Usuario
) -> None:
    registro = conversa(db, usuario, "X")
    grupo = cliente.post(f"{URL}/grupos", json={"nome": "G"}, headers=autenticado).json()

    dentro = cliente.patch(
        f"{URL}/conversas/{registro.id}", json={"grupo_id": grupo["id"]}, headers=autenticado
    ).json()
    fora = cliente.patch(
        f"{URL}/conversas/{registro.id}", json={"grupo_id": None}, headers=autenticado
    ).json()

    assert dentro["grupo_id"] == grupo["id"]
    assert fora["grupo_id"] is None


def test_apagar_grupo_solta_as_conversas(
    cliente: TestClient, autenticado: dict[str, str], db: Session, usuario: Usuario
) -> None:
    registro = conversa(db, usuario, "Fica")
    grupo = cliente.post(
        f"{URL}/grupos", json={"nome": "G", "conversa_ids": [registro.id]}, headers=autenticado
    ).json()

    resposta = cliente.delete(f"{URL}/grupos/{grupo['id']}", headers=autenticado)

    assert resposta.status_code == 204
    db.expire_all()
    assert db.get(GrupoChat, grupo["id"]) is None
    assert db.get(Conversa, registro.id).grupo_id is None


def test_grupo_e_conversa_de_outro_aluno_sao_404(
    cliente: TestClient, autenticado: dict[str, str], db: Session, usuario: Usuario, outro: Usuario
) -> None:
    alheia = conversa(db, outro, "Da Bia")
    grupo_alheio = GrupoChat(usuario_id=outro.id, nome="Dela")
    db.add(grupo_alheio)
    db.commit()
    minha = conversa(db, usuario, "Minha")

    com_alheia = cliente.post(
        f"{URL}/grupos", json={"nome": "G", "conversa_ids": [alheia.id]}, headers=autenticado
    )
    para_grupo_alheio = cliente.patch(
        f"{URL}/conversas/{minha.id}", json={"grupo_id": grupo_alheio.id}, headers=autenticado
    )

    assert com_alheia.status_code == 404
    assert para_grupo_alheio.status_code == 404
    assert cliente.get(f"{URL}/grupos/{grupo_alheio.id}", headers=autenticado).status_code == 404
    assert cliente.get(f"{URL}/grupos", headers=autenticado).json() == []
    db.expire_all()
    assert db.scalars(select(GrupoChat).where(GrupoChat.usuario_id == usuario.id)).all() == []


# --- sugestões ----------------------------------------------------------------------------


def test_sugestoes_trazem_o_passo_atual_e_as_conversas_recentes(
    cliente: TestClient, autenticado: dict[str, str], db: Session, usuario: Usuario
) -> None:
    trilha = Trilha(slug="py", nome="Python", disciplina="Algoritmos", publicada=True)
    trilha.modulos = [Modulo(ordem=1, titulo="Laços")]
    db.add(trilha)
    db.commit()
    db.add(
        ProgressoUsuario(
            usuario_id=usuario.id,
            trilha_id=trilha.id,
            modulo_id=trilha.modulos[0].id,
            status=StatusProgresso.em_andamento,
        )
    )
    db.commit()
    recente = conversa(db, usuario, "Funções")
    conversa(db, usuario, "Nova conversa")
    arquivada = conversa(db, usuario, "Arquivada")
    arquivada.arquivada = True
    db.commit()

    corpo = cliente.get(f"{URL}/sugestoes", headers=autenticado).json()

    assert corpo[0]["origem"] == "trilha"
    assert "Laços" in corpo[0]["texto"]
    assert corpo[1:] == [{"texto": "Funções", "origem": "conversa", "conversa_id": recente.id}]


# --- full-text no PostgreSQL --------------------------------------------------------------


@pytest.mark.postgres
def test_busca_no_postgres_usa_o_radical_em_portugues(db_postgres: Session) -> None:
    from app.schemas.pagina import Paginacao
    from app.services import conversas as servico

    dono = Usuario(email="fts-chat@ufrpe.br", username="fts-chat", nome_exibicao="FTS")
    db_postgres.add(dono)
    db_postgres.commit()
    conversa(db_postgres, dono, "Dúvida", "Não entendi os laços aninhados")
    conversa(db_postgres, dono, "Outra", "Como abrir um arquivo?")

    itens, total = servico.listar(
        db_postgres, dono, Paginacao(pagina=1, tamanho_pagina=10), busca="laço"
    )

    assert (total, [c.titulo for c in itens]) == (1, ["Dúvida"])
