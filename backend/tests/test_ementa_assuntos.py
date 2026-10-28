"""Da ementa aos assuntos e ao catálogo (#38): a skill `ler_ementa`, o mapeamento e as rotas.

O provedor falso responde a leitura pronta e dá a cada texto um embedding por
tema (variáveis, condicionais, repetição, recursão): o que fala do mesmo tema
fica à distância 0, e o resto, a 1. Assim o teste diz qual assunto deve cair em
qual módulo sem depender de um modelo de verdade.
"""

import asyncio
import json
from collections.abc import AsyncGenerator, Iterator, Sequence
from pathlib import Path
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ia import IAIndisponivel, MensagemIA, get_provedor_ia
from app.ia.base import DIMENSOES_EMBEDDING
from app.ia.ollama import Ollama
from app.ia.skills import ler_ementa
from app.main import app
from app.models import (
    AssuntoEmenta,
    Ementa,
    Lacuna,
    Modulo,
    StatusAssuntos,
    StatusEmenta,
    Trilha,
    Usuario,
)
from app.services import assuntos_ementa
from app.services import auth as servico_auth
from tests.test_onboarding import TEXTO_DA_EMENTA, pdf_com_texto

DISCIPLINA = "Introdução à Programação"

LEITURA = {
    "disciplinas": [
        {
            "nome": DISCIPLINA,
            "periodo": 1,
            "carga_horaria": 60,
            "assuntos": [
                "Variáveis e tipos",
                "Estruturas condicionais",
                "Laços de repetição",
                "Recursão",
            ],
        }
    ]
}

TEMAS = ["variave", "condiciona", "repeticao", "recurs"]


def vetor_por_tema(texto: str) -> list[float]:
    normal = ler_ementa.normalizar(texto)
    vetor = [0.0] * DIMENSOES_EMBEDDING
    for posicao, raiz in enumerate(TEMAS):
        if raiz in normal:
            vetor[posicao] = 1.0
    return vetor


class ProvedorDeEmenta:
    def __init__(self) -> None:
        self.respostas = [json.dumps(LEITURA)]
        self.chamadas: list[tuple[list[MensagemIA], dict[str, Any] | None]] = []
        self.gerar_fora = False
        self.embeddings_fora = False
        # Cada texto que pediu embedding, na ordem.
        self.embedados: list[str] = []

    async def gerar(
        self,
        mensagens: Sequence[MensagemIA],
        *,
        max_tokens: int,
        formato: dict[str, Any] | None = None,
    ) -> AsyncGenerator[str]:
        if self.gerar_fora:
            raise IAIndisponivel("fora (simulado no teste)")
        self.chamadas.append((list(mensagens), formato))
        resposta = self.respostas[min(len(self.chamadas), len(self.respostas)) - 1]
        for inicio in range(0, len(resposta), 10):
            yield resposta[inicio : inicio + 10]

    async def embeddings(self, textos: Sequence[str]) -> list[list[float]]:
        if self.embeddings_fora:
            raise IAIndisponivel("fora (simulado no teste)")
        self.embedados.extend(textos)
        return [vetor_por_tema(texto) for texto in textos]


@pytest.fixture
def midia(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "diretorio_midia", str(tmp_path))
    return tmp_path


@pytest.fixture
def provedor(cliente: TestClient) -> Iterator[ProvedorDeEmenta]:
    """Depende do `cliente` para trocar o `Eco` que ele instala."""
    falso = ProvedorDeEmenta()
    app.dependency_overrides[get_provedor_ia] = lambda: falso
    yield falso


@pytest.fixture
def catalogo(db: Session) -> list[Modulo]:
    trilha = Trilha(slug="ip", nome="Primeiros passos", disciplina=DISCIPLINA, periodo=1)
    trilha.modulos = [
        Modulo(ordem=1, titulo="Variáveis e tipos de dados"),
        Modulo(ordem=2, titulo="Estruturas condicionais", descricao="if, elif e else"),
        Modulo(ordem=3, titulo="Laços de repetição"),
    ]
    db.add(trilha)
    db.commit()
    return trilha.modulos


def enviar(cliente: TestClient, headers: dict[str, str], linhas: list[str] = TEXTO_DA_EMENTA):
    resposta = cliente.post(
        "/api/v1/ementas",
        headers=headers,
        files={"arquivo": ("ementa.pdf", pdf_com_texto(linhas), "application/pdf")},
    )
    assert resposta.status_code == 202, resposta.text
    return resposta.json()["id"]


def assuntos(cliente: TestClient, headers: dict[str, str], ementa_id: int) -> dict:
    resposta = cliente.get(f"/api/v1/ementas/{ementa_id}/assuntos", headers=headers)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def situacoes(corpo: dict) -> dict[str, str]:
    return {a["texto"]: a["situacao"] for d in corpo["disciplinas"] for a in d["assuntos"]}


# --- critério de aceite -------------------------------------------------------------------


def test_ementa_vira_disciplinas_com_assuntos_cobertos_e_lacunas(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorDeEmenta,
    catalogo: list[Modulo],
    midia: Path,
) -> None:
    """O critério da #38 sem a tela de revisão: o que o catálogo tem e o que falta."""
    ementa_id = enviar(cliente, autenticado)

    status = cliente.get(f"/api/v1/ementas/{ementa_id}", headers=autenticado).json()
    assert (status["status"], status["status_assuntos"]) == ("processada", "prontos")

    corpo = assuntos(cliente, autenticado, ementa_id)
    [disciplina] = corpo["disciplinas"]
    assert (disciplina["nome"], disciplina["periodo"], disciplina["carga_horaria"]) == (
        DISCIPLINA,
        1,
        60,
    )
    variaveis, condicionais, lacos, recursao = disciplina["assuntos"]
    assert [variaveis["modulo"]["id"], condicionais["modulo"]["id"], lacos["modulo"]["id"]] == [
        m.id for m in catalogo
    ]
    assert {variaveis["situacao"], condicionais["situacao"], lacos["situacao"]} == {"coberto"}
    assert recursao == {
        "texto": "Recursão",
        "situacao": "lacuna",
        "modulo": None,
        "status_lacuna": "pendente",
    }


def test_a_ia_recebe_o_texto_do_pdf_e_o_formato_da_resposta(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorDeEmenta,
    catalogo: list[Modulo],
    midia: Path,
) -> None:
    enviar(cliente, autenticado)

    [(mensagens, formato)] = provedor.chamadas
    assert mensagens[0].conteudo == ler_ementa.PROMPT
    assert "Conteudo programatico: variaveis" in mensagens[1].conteudo
    assert formato == ler_ementa.FORMATO


def test_distancia_ate_o_modulo_mais_proximo_fica_gravada(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorDeEmenta,
    catalogo: list[Modulo],
    midia: Path,
    db: Session,
) -> None:
    enviar(cliente, autenticado)

    distancias = db.scalars(select(AssuntoEmenta.distancia).order_by(AssuntoEmenta.ordem)).all()
    assert distancias == [0.0, 0.0, 0.0, 1.0]


# --- lacunas ------------------------------------------------------------------------------


def test_mesmo_assunto_em_duas_ementas_e_uma_lacuna_so(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorDeEmenta,
    catalogo: list[Modulo],
    midia: Path,
    db: Session,
) -> None:
    """A busca de conteúdo (#207) roda uma vez por assunto, não uma por aluno."""
    primeira = enviar(cliente, autenticado)
    segunda = enviar(cliente, autenticado, [*TEXTO_DA_EMENTA, "Outra turma"])

    assert db.scalar(select(func.count()).select_from(Lacuna)) == 1
    lacuna = db.scalars(select(Lacuna)).one()
    assert (lacuna.disciplina, lacuna.assunto) == (DISCIPLINA, "Recursão")
    ligadas = db.scalars(select(AssuntoEmenta).where(AssuntoEmenta.lacuna_id == lacuna.id)).all()
    assert {a.disciplina.ementa_id for a in ligadas} == {primeira, segunda}


def test_catalogo_que_cresceu_cobre_a_lacuna_na_releitura(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorDeEmenta,
    catalogo: list[Modulo],
    midia: Path,
    db: Session,
) -> None:
    ementa_id = enviar(cliente, autenticado)
    recursao = Modulo(trilha_id=catalogo[0].trilha_id, ordem=4, titulo="Recursão")
    db.add(recursao)
    db.commit()

    resposta = cliente.post(f"/api/v1/ementas/{ementa_id}/assuntos", headers=autenticado)

    assert resposta.status_code == 202, resposta.text
    corpo = assuntos(cliente, autenticado, ementa_id)
    assert set(situacoes(corpo).values()) == {"coberto"}
    assert corpo["disciplinas"][0]["assuntos"][3]["modulo"]["id"] == recursao.id


# --- reaproveitamento ---------------------------------------------------------------------


def test_mesmo_pdf_reaproveita_a_leitura_sem_chamar_a_ia(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorDeEmenta,
    catalogo: list[Modulo],
    midia: Path,
) -> None:
    primeira = enviar(cliente, autenticado)
    segunda = enviar(cliente, autenticado)

    assert len(provedor.chamadas) == 1
    assert assuntos(cliente, autenticado, segunda) == assuntos(cliente, autenticado, primeira)


# --- falhas -------------------------------------------------------------------------------


def test_ia_fora_deixa_o_texto_lido_e_a_releitura_recupera(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorDeEmenta,
    catalogo: list[Modulo],
    midia: Path,
) -> None:
    provedor.gerar_fora = True
    ementa_id = enviar(cliente, autenticado)

    status = cliente.get(f"/api/v1/ementas/{ementa_id}", headers=autenticado).json()
    assert (status["status"], status["status_assuntos"]) == ("processada", "falhou")
    assert status["erro_assuntos"] == assuntos_ementa.ERRO_IA_FORA
    assert assuntos(cliente, autenticado, ementa_id)["disciplinas"] == []

    provedor.gerar_fora = False
    resposta = cliente.post(f"/api/v1/ementas/{ementa_id}/assuntos", headers=autenticado)

    assert resposta.status_code == 202
    corpo = assuntos(cliente, autenticado, ementa_id)
    assert (corpo["status_assuntos"], corpo["erro_assuntos"]) == ("prontos", None)
    assert len(situacoes(corpo)) == 4


@pytest.mark.parametrize(
    ("resposta", "erro"),
    [
        ("Não encontrei disciplinas.", assuntos_ementa.ERRO_SAIDA_INVALIDA),
        ('{"disciplinas": [{"nome": "IP", "periodo": 0}]}', assuntos_ementa.ERRO_SAIDA_INVALIDA),
        ('{"disciplinas": []}', assuntos_ementa.ERRO_SEM_DISCIPLINAS),
        ('{"disciplinas": [{"nome": "IP", "assuntos": []}]}', assuntos_ementa.ERRO_SEM_DISCIPLINAS),
    ],
)
def test_leitura_invalida_ou_vazia_e_descartada(
    cliente: TestClient,
    autenticado: dict[str, str],
    provedor: ProvedorDeEmenta,
    catalogo: list[Modulo],
    midia: Path,
    db: Session,
    resposta: str,
    erro: str,
) -> None:
    provedor.respostas = [resposta]
    ementa_id = enviar(cliente, autenticado)

    status = cliente.get(f"/api/v1/ementas/{ementa_id}", headers=autenticado).json()
    assert (status["status_assuntos"], status["erro_assuntos"]) == ("falhou", erro)
    assert db.scalar(select(func.count()).select_from(AssuntoEmenta)) == 0
    assert db.scalar(select(func.count()).select_from(Lacuna)) == 0


def test_releitura_antes_do_texto_responde_409(
    cliente: TestClient, autenticado: dict[str, str], usuario: Usuario, db: Session
) -> None:
    ementa = Ementa(usuario_id=usuario.id, arquivo_path="x.pdf", status=StatusEmenta.processando)
    db.add(ementa)
    db.commit()

    resposta = cliente.post(f"/api/v1/ementas/{ementa.id}/assuntos", headers=autenticado)

    assert resposta.status_code == 409
    assert resposta.json()["erro"]["code"] == "assuntos_indisponiveis"
    db.refresh(ementa)
    assert ementa.status_assuntos is StatusAssuntos.pendente


def test_assuntos_da_ementa_de_outro_aluno_respondem_404(
    cliente: TestClient, autenticado: dict[str, str], db: Session
) -> None:
    outro = servico_auth.registrar(
        db, email="bia@ufrpe.br", senha="Outra-Senha-2026", username="bia", nome_exibicao="Bia"
    )
    ementa = Ementa(usuario_id=outro.id, arquivo_path="x.pdf", status=StatusEmenta.processada)
    db.add(ementa)
    db.commit()

    for metodo in (cliente.get, cliente.post):
        resposta = metodo(f"/api/v1/ementas/{ementa.id}/assuntos", headers=autenticado)
        assert resposta.status_code == 404


# --- skill --------------------------------------------------------------------------------


def test_texto_longo_vai_em_partes_cortadas_entre_linhas() -> None:
    texto = "\n".join(f"Linha {i:02d} da ementa" for i in range(10))

    partes = ler_ementa.dividir_texto(texto, tamanho=40)

    assert partes == [
        "Linha 00 da ementa\nLinha 01 da ementa",
        "Linha 02 da ementa\nLinha 03 da ementa",
        "Linha 04 da ementa\nLinha 05 da ementa",
        "Linha 06 da ementa\nLinha 07 da ementa",
        "Linha 08 da ementa\nLinha 09 da ementa",
    ]
    assert ler_ementa.dividir_texto("x" * 25, tamanho=10) == ["x" * 10, "x" * 10, "x" * 5]
    assert ler_ementa.dividir_texto("  \n\n ") == []


def test_resposta_embrulhada_em_cerca_de_codigo_e_aceita() -> None:
    leitura = ler_ementa.ler_resposta(f"```json\n{json.dumps(LEITURA)}\n```")

    assert leitura.disciplinas[0].assuntos[0] == "Variáveis e tipos"


def test_disciplina_partida_entre_duas_partes_vira_uma_so() -> None:
    primeira = ler_ementa.Leitura.model_validate(
        {"disciplinas": [{"nome": "Algoritmos", "assuntos": ["Laços", "Funções"]}]}
    )
    segunda = ler_ementa.Leitura.model_validate(
        {
            "disciplinas": [
                {"nome": "ALGORITMOS", "periodo": 2, "assuntos": ["funções", "Recursão"]},
                {"nome": "Banco de Dados", "assuntos": ["SQL"]},
            ]
        }
    )

    juntas = ler_ementa.juntar([primeira, segunda])

    assert [(d.nome, d.periodo, d.assuntos) for d in juntas] == [
        ("Algoritmos", 2, ["Laços", "Funções", "Recursão"]),
        ("Banco de Dados", None, ["SQL"]),
    ]


def test_ollama_pede_o_formato_da_resposta() -> None:
    pedidos: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        pedidos.append(request)
        return httpx2.Response(200, content=b'{"message": {"content": "{}"}, "done": true}\n')

    ollama = Ollama(
        "http://ollama.teste",
        "llama3.2",
        timeout_conexao=1,
        timeout_leitura=1,
        tentativas=1,
        transport=httpx2.MockTransport(handler),
    )

    async def ler() -> str:
        mensagens = ler_ementa.mensagens("texto")
        return "".join(
            [p async for p in ollama.gerar(mensagens, max_tokens=10, formato=ler_ementa.FORMATO)]
        )

    assert asyncio.run(ler()) == "{}"
    assert json.loads(pedidos[0].content)["format"] == ler_ementa.FORMATO


# --- PostgreSQL de verdade ------------------------------------------------------------------


@pytest.mark.postgres
def test_mapeamento_no_pgvector_cobre_e_abre_uma_lacuna_so(db_postgres: Session) -> None:
    """O mapeamento pelo `cosine_distance` e a lacuna única pela constraint do banco."""
    provedor = ProvedorDeEmenta()
    provedor.respostas = [
        json.dumps({"disciplinas": [{"nome": "Vault Teste", "assuntos": ["Recursão", "Grafos"]}]})
    ]
    trilha = Trilha(slug="ementa-teste-pg", nome="Ementa", disciplina="Vault Teste", periodo=1)
    trilha.modulos = [Modulo(ordem=1, titulo="Recursão em profundidade")]
    db_postgres.add(trilha)
    aluno = servico_auth.registrar(
        db_postgres,
        email="ementa-pg@ufrpe.br",
        senha="Trilha-Boa-2026",
        username="ementa_pg",
        nome_exibicao="Ementa PG",
    )
    ementas = [
        Ementa(
            usuario_id=aluno.id,
            arquivo_path=f"{i}.pdf",
            status=StatusEmenta.processada,
            texto_extraido=f"Ementa {i}",
        )
        for i in range(2)
    ]
    db_postgres.add_all(ementas)
    db_postgres.commit()

    for ementa in ementas:
        asyncio.run(assuntos_ementa.processar(db_postgres, provedor, ementa))

    for ementa in ementas:
        assert ementa.status_assuntos is StatusAssuntos.prontos, ementa.erro_assuntos
        recursao, grafos = ementa.disciplinas[0].assuntos
        assert (recursao.modulo_id, recursao.lacuna_id) == (trilha.modulos[0].id, None)
        assert grafos.modulo_id is None
    lacunas = db_postgres.scalars(select(Lacuna).where(Lacuna.disciplina == "Vault Teste")).all()
    assert [lacuna.assunto for lacuna in lacunas] == ["Grafos"]
