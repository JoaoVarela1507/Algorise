"""Onde está o ementário num PPC: marcadores do PDF, sumário e densidade.

As páginas aqui já são texto: o que se testa é a busca, não o pypdf. O caminho
do PDF de verdade, do upload ao texto guardado, está em `test_onboarding.py`,
e o dos marcadores, no último teste daqui.
"""

from io import BytesIO

from pypdf import PdfReader, PdfWriter

from app.services import ppc
from app.services.ementas import _marcadores
from tests.test_onboarding import pdf_com_paginas

EMENTA = "Ementa: algoritmos.\nCarga horária: 60 h\nBibliografia básica: Pense em Python."


def documento(total: int = 40) -> list[str]:
    return [f"Texto institucional da página {i + 1}." for i in range(total)]


def test_marcadores_vao_do_item_do_ementario_ao_seguinte() -> None:
    marcadores = [("Apresentação", 2), ("Matriz curricular", 10), ("Ementário", 20), ("Anexos", 31)]

    assert ppc.localizar(documento(), marcadores) == ppc.Trecho(20, 30, "marcadores")


def test_ementario_no_ultimo_marcador_vai_ate_o_fim() -> None:
    marcadores = [("Apresentação", 2), ("EMENTAS DAS DISCIPLINAS", 35)]

    assert ppc.localizar(documento(), marcadores) == ppc.Trecho(35, 39, "marcadores")


def test_sumario_acha_o_cabecalho_e_corrige_o_deslocamento() -> None:
    """O sumário diz 18, mas a capa e o sumário empurram o capítulo duas páginas."""
    paginas = documento()
    paginas[1] = "SUMÁRIO\n1 APRESENTAÇÃO ........ 3\n6 EMENTÁRIO .......... 18\n7 ANEXOS ...... 25"
    paginas[19] = "6 EMENTÁRIO\n" + EMENTA

    assert ppc.localizar(paginas) == ppc.Trecho(19, 25, "sumario")


def test_sumario_sem_pontilhado_tambem_serve() -> None:
    """O pypdf costuma juntar o pontilhado em espaço."""
    paginas = documento()
    paginas[2] = "Sumário\n1 Apresentação 3\n5 Ementário 30\n6 Referências 36"
    paginas[31] = "5 Ementário\n" + EMENTA

    assert ppc.localizar(paginas) == ppc.Trecho(31, 36, "sumario")


def test_sumario_sem_cabecalho_usa_o_numero_impresso() -> None:
    paginas = documento()
    paginas[1] = "SUMÁRIO\nEMENTÁRIO ........ 12\nANEXOS ........ 20"

    assert ppc.localizar(paginas) == ppc.Trecho(11, 18, "sumario")


def test_entrada_de_sumario_fora_do_documento_e_ignorada() -> None:
    paginas = documento(10)
    paginas[1] = "SUMÁRIO\nEMENTÁRIO ........ 300"

    assert ppc.localizar(paginas).metodo == "documento"


def test_sem_indice_o_trecho_mais_denso_em_ementas() -> None:
    """Uma página solta no meio (o cabeçalho de um período) não quebra o trecho."""
    paginas = documento()
    for i in (5, 22, 23, 25, 26, 27):
        paginas[i] = EMENTA
    paginas[24] = "2º PERÍODO"

    assert ppc.localizar(paginas) == ppc.Trecho(22, 27, "densidade")


def test_ementa_curta_sem_nada_disso_e_lida_inteira() -> None:
    assert ppc.localizar(["Introdução à Programação", EMENTA]) == ppc.Trecho(0, 1, "documento")
    assert ppc.localizar([]) == ppc.Trecho(0, 0, "documento")


def test_marcadores_saem_do_indice_lateral_do_pdf() -> None:
    escritor = PdfWriter()
    escritor.append(PdfReader(BytesIO(pdf_com_paginas([[f"Pagina {i}"] for i in range(6)]))))
    capitulo = escritor.add_outline_item("Ementário", 3)
    escritor.add_outline_item("Introdução à Programação", 4, parent=capitulo)
    escritor.add_outline_item("Anexos", 5)
    saida = BytesIO()
    escritor.write(saida)

    leitor = PdfReader(BytesIO(saida.getvalue()))

    assert _marcadores(leitor) == [
        ("Ementário", 3),
        ("Introdução à Programação", 4),
        ("Anexos", 5),
    ]
