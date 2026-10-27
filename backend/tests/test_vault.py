"""Vault das skills (#200): transcrições, trechos, ingestão e busca.

A busca roda aqui no SQLite, com a distância calculada em Python e o embedding
falso do `Eco`. O caminho do pgvector tem o próprio teste, marcado `postgres`,
que só roda com `TESTE_POSTGRES_URL` (o CI liga).
"""

import asyncio
import json
import os
from collections.abc import Iterator, Sequence
from pathlib import Path

import httpx2
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.ia import IAIndisponivel
from app.ia.base import DIMENSOES_EMBEDDING
from app.ia.eco import Eco, vetor_de_palavras
from app.ia.ollama import Ollama
from app.ia.vault import (
    ModuloNaoEncontrado,
    buscar,
    ingerir_transcricao,
    registrar_prompts,
)
from app.ia.vault import __main__ as linha_de_comando
from app.ia.vault.busca import distancia_cosseno
from app.ia.vault.trechos import Fala, dividir, ler_transcricao
from app.models import DocumentoVault, Modulo, OrigemVault, TrechoVault, Trilha

VTT = """﻿WEBVTT

NOTE gravado na aula 3

00:00.000 --> 00:04.000
<v Professor>Um laço repete um bloco de código.</v>

00:04.000 --> 00:08.500
<v Professor>Um laço repete um bloco de código.</v>

00:01:08.500 --> 00:01:12.000
O <c.destaque>for</c> percorre uma lista.
"""

SRT = """1
00:00:01,000 --> 00:00:03,000
Uma função recebe parâmetros.

2
01:00:02,250 --> 01:00:05,000
E devolve um valor
com return.
"""

LACOS = (
    "O laço for percorre cada item de uma lista. O laço while repete enquanto a condição "
    "for verdadeira. Um laço infinito acontece quando a condição nunca fica falsa."
)
FUNCOES = (
    "Uma função recebe parâmetros e devolve um valor com return. Chamar a função executa "
    "o corpo dela. Parâmetros com valor padrão são opcionais na chamada."
)


class ProvedorContado(Eco):
    """O `Eco`, contando os pedidos de embedding e falhando quando o teste mandar."""

    def __init__(self) -> None:
        self.pedidos: list[list[str]] = []
        self.falhar = False

    async def embeddings(self, textos: Sequence[str]) -> list[list[float]]:
        if self.falhar:
            raise IAIndisponivel("fora (simulado no teste)")
        self.pedidos.append(list(textos))
        return await super().embeddings(textos)


@pytest.fixture
def provedor() -> ProvedorContado:
    return ProvedorContado()


def criar_modulos(db: Session) -> tuple[Modulo, Modulo, Modulo]:
    """Dois módulos de Algoritmos (laços e funções) e um de outra disciplina."""
    algoritmos = Trilha(slug="python", nome="Python", disciplina="Algoritmos", periodo=1)
    algoritmos.modulos = [
        Modulo(ordem=1, titulo="Laços"),
        Modulo(ordem=2, titulo="Funções"),
    ]
    banco = Trilha(slug="sql", nome="SQL", disciplina="Banco de Dados", periodo=3)
    banco.modulos = [Modulo(ordem=1, titulo="Consultas")]
    db.add_all([algoritmos, banco])
    db.commit()
    lacos, funcoes = algoritmos.modulos
    return lacos, funcoes, banco.modulos[0]


def ingerir(db: Session, provedor: Eco, modulo: Modulo, texto: str, nome: str = "aula.txt"):
    return asyncio.run(
        ingerir_transcricao(db, provedor, modulo_id=modulo.id, conteudo=texto, nome_arquivo=nome)
    )


# --- leitura das transcrições --------------------------------------------------


def test_vtt_tira_cabecalho_marcacao_e_repeticao_e_guarda_o_tempo() -> None:
    falas = ler_transcricao(VTT, "aula.VTT")

    assert falas == [
        Fala("Um laço repete um bloco de código.", 0.0),
        Fala("O for percorre uma lista.", 68.5),
    ]


def test_srt_junta_as_linhas_da_fala_e_le_as_horas() -> None:
    falas = ler_transcricao(SRT.replace("\n", "\r\n"), "aula.srt")

    assert falas == [
        Fala("Uma função recebe parâmetros.", 1.0),
        Fala("E devolve um valor com return.", 3602.25),
    ]


def test_texto_corrido_vira_uma_fala_por_paragrafo_sem_tempo() -> None:
    falas = ler_transcricao("Primeiro   parágrafo\ncontinua.\n\n\nSegundo.\n", "aula.txt")

    assert falas == [Fala("Primeiro parágrafo continua."), Fala("Segundo.")]


# --- divisão em trechos ----------------------------------------------------------


def test_trecho_corta_entre_frases_e_repete_o_fim_do_anterior() -> None:
    frases = [Fala(f"Frase número {i} do texto.", float(i)) for i in range(10)]

    trechos = dividir(frases, tamanho=80, sobreposicao=30)

    assert len(trechos) > 1
    for trecho in trechos:
        assert len(trecho.texto) <= 80
        assert trecho.texto.endswith(".")
    # A última frase de um trecho abre o seguinte.
    assert trechos[1].texto.startswith(trechos[0].texto.split(". ")[-1])
    # O tempo do trecho é o da primeira frase dele.
    assert trechos[0].inicio == 0.0
    assert trechos[1].inicio > 0


def test_frase_sem_pontuacao_maior_que_o_trecho_e_cortada_entre_palavras() -> None:
    legenda = " ".join(f"palavra{i}" for i in range(60))

    trechos = dividir([Fala(legenda)], tamanho=100, sobreposicao=0)

    assert all(len(t.texto) <= 100 for t in trechos)
    assert " ".join(t.texto for t in trechos) == legenda


def test_sem_texto_nao_ha_trecho() -> None:
    assert dividir([]) == []
    assert dividir([Fala("   ")]) == []


# --- ingestão ------------------------------------------------------------------------


def test_ingerir_grava_trechos_com_embedding_e_tempo(db: Session, provedor: ProvedorContado):
    lacos, _, _ = criar_modulos(db)

    ingestao = ingerir(db, provedor, lacos, VTT, "aula.vtt")

    documento = ingestao.documento
    assert ingestao.alterado
    assert (documento.chave, documento.origem, documento.versao) == (
        "modulo:1",
        OrigemVault.transcricao,
        1,
    )
    assert documento.titulo == "Laços"
    assert [t.inicio_segundos for t in documento.trechos] == [0.0]
    assert len(documento.trechos[0].embedding) == DIMENSOES_EMBEDDING


def test_reingerir_o_mesmo_conteudo_nao_refaz_nada(db: Session, provedor: ProvedorContado):
    lacos, _, _ = criar_modulos(db)
    ingerir(db, provedor, lacos, LACOS)

    ingestao = ingerir(db, provedor, lacos, LACOS)

    assert not ingestao.alterado
    assert ingestao.documento.versao == 1
    assert len(provedor.pedidos) == 1


def test_conteudo_novo_substitui_os_trechos_sem_duplicar(db: Session, provedor: ProvedorContado):
    lacos, _, _ = criar_modulos(db)
    ingerir(db, provedor, lacos, LACOS)

    ingestao = ingerir(db, provedor, lacos, FUNCOES)

    assert ingestao.alterado
    assert ingestao.documento.versao == 2
    assert db.scalar(select(func.count()).select_from(DocumentoVault)) == 1
    textos = db.scalars(select(TrechoVault.texto)).all()
    assert textos == [FUNCOES]


def test_provedor_fora_mantem_a_versao_anterior(db: Session, provedor: ProvedorContado):
    lacos, _, _ = criar_modulos(db)
    ingerir(db, provedor, lacos, LACOS)
    provedor.falhar = True

    with pytest.raises(IAIndisponivel):
        ingerir(db, provedor, lacos, FUNCOES)

    db.rollback()
    assert db.scalars(select(TrechoVault.texto)).all() == [LACOS]


def test_transcricao_longa_vai_em_lotes(db: Session, provedor: ProvedorContado):
    lacos, _, _ = criar_modulos(db)
    longo = " ".join(f"Frase {i} sobre laços em Python." for i in range(1500))

    ingestao = ingerir(db, provedor, lacos, longo)

    assert len(ingestao.documento.trechos) > 32
    assert all(len(pedido) <= 32 for pedido in provedor.pedidos)


def test_modulo_inexistente_e_recusado(db: Session, provedor: ProvedorContado):
    with pytest.raises(ModuloNaoEncontrado):
        asyncio.run(
            ingerir_transcricao(db, provedor, modulo_id=99, conteudo="x", nome_arquivo="a.txt")
        )


def test_registrar_prompts_grava_o_do_tutor_uma_vez(db: Session, provedor: ProvedorContado):
    primeira = asyncio.run(registrar_prompts(db, provedor))
    segunda = asyncio.run(registrar_prompts(db, provedor))

    tutor = next(i.documento for i in primeira if i.documento.chave == "skill:tutor")
    assert (tutor.origem, tutor.skill, tutor.modulo_id) == (OrigemVault.prompt, "tutor", None)
    assert "tutor do Algorise" in tutor.trechos[0].texto
    assert not any(i.alterado for i in segunda)


# --- busca -----------------------------------------------------------------------------


def test_busca_traz_primeiro_o_trecho_do_video_do_assunto(db: Session, provedor: Eco):
    """O critério de aceite da #200."""
    lacos, funcoes, _ = criar_modulos(db)
    ingerir(db, provedor, lacos, LACOS)
    ingerir(db, provedor, funcoes, FUNCOES)

    resultados = asyncio.run(buscar(db, provedor, "como funciona o laço while?"))

    assert [r.modulo_id for r in resultados] == [lacos.id, funcoes.id]
    assert resultados[0].distancia < resultados[1].distancia
    assert resultados[0].titulo == "Laços"

    resultados = asyncio.run(buscar(db, provedor, "o que o return devolve da função?"))
    assert resultados[0].modulo_id == funcoes.id


def test_busca_filtra_por_trilha_disciplina_e_origem(db: Session, provedor: Eco):
    lacos, _, consultas = criar_modulos(db)
    ingerir(db, provedor, lacos, LACOS)
    ingerir(db, provedor, consultas, "O SELECT lê linhas de uma tabela com WHERE e laço.")
    asyncio.run(registrar_prompts(db, provedor))

    por_trilha = asyncio.run(buscar(db, provedor, "laço", trilha_id=consultas.trilha_id))
    por_disciplina = asyncio.run(buscar(db, provedor, "laço", disciplina="algoritmos"))
    so_prompts = asyncio.run(buscar(db, provedor, "tutor", origem=OrigemVault.prompt))

    assert {r.modulo_id for r in por_trilha} == {consultas.id}
    assert {r.modulo_id for r in por_disciplina} == {lacos.id}
    assert so_prompts and {r.origem for r in so_prompts} == {OrigemVault.prompt}


def test_busca_respeita_o_limite(db: Session, provedor: Eco):
    lacos, _, _ = criar_modulos(db)
    ingerir(db, provedor, lacos, " ".join([LACOS] * 20))

    assert len(asyncio.run(buscar(db, provedor, "laço", limite=2))) == 2


def test_distancia_de_cosseno() -> None:
    assert distancia_cosseno([1, 0], [1, 0]) == 0
    assert distancia_cosseno([1, 0], [0, 1]) == 1
    assert distancia_cosseno([1, 0], [-1, 0]) == 2
    assert distancia_cosseno([0, 0], [1, 0]) == 1


def test_embedding_do_eco_e_estavel_e_ignora_acento_e_caixa() -> None:
    assert vetor_de_palavras("Laço de repetição") == vetor_de_palavras("laco DE repeticao")
    assert len(vetor_de_palavras("")) == DIMENSOES_EMBEDDING


# --- linha de comando --------------------------------------------------------------------


def test_linha_de_comando_ingere_e_registra(
    db: Session,
    sessao_factory,
    provedor: ProvedorContado,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lacos, _, _ = criar_modulos(db)
    arquivo = tmp_path / "aula.vtt"
    arquivo.write_text(VTT, encoding="utf-8")
    monkeypatch.setattr(linha_de_comando, "SessionLocal", sessao_factory)
    monkeypatch.setattr(linha_de_comando, "get_provedor_ia", lambda: provedor)

    assert linha_de_comando.main(["ingerir", "--modulo", str(lacos.id), str(arquivo)]) == 0
    assert linha_de_comando.main(["ingerir", "--modulo", str(lacos.id), str(arquivo)]) == 0
    assert linha_de_comando.main(["registrar-prompts"]) == 0
    assert linha_de_comando.main(["ingerir", "--modulo", "99", str(arquivo)]) == 1

    saida = capsys.readouterr()
    assert "modulo:1: versão 1, 1 trechos" in saida.out
    assert "modulo:1: sem mudança (versão 1)" in saida.out
    assert "skill:tutor: versão 1" in saida.out
    assert "Módulo 99 não existe" in saida.err


# --- embeddings no Ollama -----------------------------------------------------------------


def ollama(handler, *, tentativas: int = 2) -> Ollama:
    return Ollama(
        "http://ollama.teste",
        "llama3.2",
        modelo_embedding="bge-m3",
        timeout_conexao=1,
        timeout_leitura=1,
        tentativas=tentativas,
        espera_entre_tentativas=0,
        transport=httpx2.MockTransport(handler),
    )


def vetores(quantidade: int, dimensoes: int = DIMENSOES_EMBEDDING) -> bytes:
    return json.dumps({"embeddings": [[0.1] * dimensoes] * quantidade}).encode()


def test_ollama_pede_todos_os_embeddings_num_pedido_so() -> None:
    pedidos: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        pedidos.append(request)
        return httpx2.Response(200, content=vetores(2))

    resultado = asyncio.run(ollama(handler).embeddings(["um", "dois"]))

    assert len(resultado) == 2
    assert pedidos[0].url.path == "/api/embed"
    assert json.loads(pedidos[0].content) == {"model": "bge-m3", "input": ["um", "dois"]}


def test_ollama_sem_texto_nao_faz_pedido() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise AssertionError("não devia pedir nada")

    assert asyncio.run(ollama(handler).embeddings([])) == []


def test_ollama_embedding_tenta_de_novo_quando_nao_conecta() -> None:
    tentativas = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        tentativas.append(request)
        if len(tentativas) == 1:
            raise httpx2.ConnectError("recusada", request=request)
        return httpx2.Response(200, content=vetores(1))

    assert len(asyncio.run(ollama(handler).embeddings(["um"]))) == 1
    assert len(tentativas) == 2


@pytest.mark.parametrize(
    ("resposta", "mensagem"),
    [
        (httpx2.Response(404, json={"error": 'model "bge-m3" not found'}), "not found"),
        (httpx2.Response(200, content=b"isto nao e json"), "fora do formato"),
        (httpx2.Response(200, content=vetores(2)), "número de vetores"),
        (httpx2.Response(200, content=vetores(1, dimensoes=768)), "1024 dimensões"),
    ],
)
def test_ollama_embedding_com_problema_vira_ia_indisponivel(
    resposta: httpx2.Response, mensagem: str
) -> None:
    with pytest.raises(IAIndisponivel, match=mensagem):
        asyncio.run(ollama(lambda _: resposta).embeddings(["um"]))


def test_ollama_fora_no_embedding_vira_ia_indisponivel() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("recusada", request=request)

    with pytest.raises(IAIndisponivel, match="Sem conexão"):
        asyncio.run(ollama(handler).embeddings(["um"]))


# --- PostgreSQL de verdade ------------------------------------------------------------------


@pytest.fixture
def db_postgres() -> Iterator[Session]:
    """Sessão num PostgreSQL já migrado, desfeita no fim do teste.

    Tudo roda dentro de uma transação que nunca é confirmada: o teste pode usar
    o banco do CI, que já tem o seed, sem deixar rastro nele.
    """
    url = os.environ.get("TESTE_POSTGRES_URL")
    if not url:
        pytest.skip("defina TESTE_POSTGRES_URL para rodar contra o PostgreSQL")
    engine = create_engine(url)
    with engine.connect() as conexao:
        transacao = conexao.begin()
        sessao = Session(bind=conexao, join_transaction_mode="create_savepoint")
        try:
            yield sessao
        finally:
            sessao.close()
            transacao.rollback()
    engine.dispose()


@pytest.mark.postgres
def test_busca_no_pgvector_ordena_pela_distancia(db_postgres: Session) -> None:
    provedor = Eco()
    trilha = Trilha(slug="vault-teste-pg", nome="Vault", disciplina="Vault Teste", periodo=1)
    trilha.modulos = [Modulo(ordem=1, titulo="Laços"), Modulo(ordem=2, titulo="Funções")]
    db_postgres.add(trilha)
    db_postgres.commit()
    lacos, funcoes = trilha.modulos
    ingerir(db_postgres, provedor, lacos, LACOS)
    ingerir(db_postgres, provedor, funcoes, FUNCOES)

    resultados = asyncio.run(
        buscar(db_postgres, provedor, "como funciona o laço while?", disciplina="Vault Teste")
    )

    assert [r.modulo_id for r in resultados] == [lacos.id, funcoes.id]
    esperado = distancia_cosseno(
        vetor_de_palavras("como funciona o laço while?"), vetor_de_palavras(LACOS)
    )
    assert resultados[0].distancia == pytest.approx(esperado, abs=1e-5)
