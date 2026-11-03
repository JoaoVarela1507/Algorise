"""Certificados das trilhas de parceiros: emissão, lista, PDF e validação (#32).

O certificado é emitido sozinho quando o aluno fecha o último passo de uma
trilha de parceiro (`emitir_se_concluiu`, chamado pela conclusão do passo). A
trilha sem parceiro não emite: é o aviso da tela 20. O código de validação é
público por natureza (vai impresso no PDF), e a validação mostra só o que o
certificado diz, sem nada mais do aluno.
"""

import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

from fpdf import FPDF
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Certificado, Modulo, ProgressoUsuario, StatusProgresso, Trilha, Usuario

logger = logging.getLogger(__name__)
# A auditoria das ações sensíveis (#39) lê este logger.
auditoria = logging.getLogger("app.auditoria")

# Sem 0/O, 1/I/L: o aluno digita o código lendo do papel.
_ALFABETO = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


@dataclass
class ItemDaLista:
    trilha: Trilha
    total_modulos: int
    concluidos: int
    certificado: Certificado | None


def emitir_se_concluiu(db: Session, usuario: Usuario, trilha: Trilha) -> Certificado | None:
    """Emite o certificado se a trilha é de parceiro e o aluno fechou todos os passos.

    Idempotente: com o certificado já emitido, devolve o mesmo.
    """
    if trilha.parceiro is None:
        return None
    existente = db.scalar(
        select(Certificado).where(
            Certificado.usuario_id == usuario.id, Certificado.trilha_id == trilha.id
        )
    )
    if existente is not None:
        return existente
    total = db.scalar(select(func.count(Modulo.id)).where(Modulo.trilha_id == trilha.id))
    if not total or _concluidos(db, usuario.id, trilha.id) < total:
        return None

    certificado = Certificado(
        usuario_id=usuario.id,
        trilha_id=trilha.id,
        codigo=_codigo_livre(db),
        parceiro=trilha.parceiro.nome,
        emitido_em=datetime.now(UTC),
        nome_aluno=usuario.nome_exibicao,
        nome_trilha=trilha.nome,
        disciplina=trilha.disciplina,
        carga_horaria=trilha.carga_horaria,
    )
    db.add(certificado)
    db.commit()
    auditoria.info(
        "certificado_emitido",
        extra={
            "evento": "certificado_emitido",
            "alvo_usuario_id": usuario.id,
            "trilha_id": trilha.id,
        },
    )
    return certificado


def listar(db: Session, usuario: Usuario) -> list[ItemDaLista]:
    """As trilhas publicadas de parceiros, com o progresso e o certificado do aluno."""
    trilhas = db.scalars(
        select(Trilha)
        .where(Trilha.publicada.is_(True), Trilha.parceiro_id.is_not(None))
        .order_by(Trilha.periodo, Trilha.nome)
    ).all()
    certificados = {
        c.trilha_id: c
        for c in db.scalars(select(Certificado).where(Certificado.usuario_id == usuario.id))
    }
    return [
        ItemDaLista(
            trilha=trilha,
            total_modulos=len(trilha.modulos),
            concluidos=_concluidos(db, usuario.id, trilha.id),
            certificado=certificados.get(trilha.id),
        )
        for trilha in trilhas
    ]


def do_aluno(db: Session, usuario: Usuario, certificado_id: int) -> Certificado | None:
    """O certificado, se for deste aluno. O de outro responde como inexistente."""
    certificado = db.get(Certificado, certificado_id)
    return certificado if certificado and certificado.usuario_id == usuario.id else None


def validar(db: Session, codigo: str) -> Certificado | None:
    normalizado = codigo.strip().upper().replace(" ", "")
    return db.scalar(select(Certificado).where(Certificado.codigo == normalizado))


def pdf(certificado: Certificado) -> bytes:
    """O PDF do certificado: nome, trilha, disciplina, carga, data, parceiro e código."""
    documento = FPDF(orientation="L", format="A4")
    documento.set_auto_page_break(False)
    documento.add_page()
    largura = documento.w - 40

    documento.set_draw_color(43, 108, 176)
    documento.set_line_width(1.5)
    documento.rect(10, 10, documento.w - 20, documento.h - 20)

    documento.set_y(32)
    documento.set_font("Helvetica", "B", 30)
    documento.cell(
        largura, 14, _latin1("Certificado de conclusão"), align="C", new_x="LMARGIN", new_y="NEXT"
    )
    documento.ln(10)
    documento.set_font("Helvetica", "", 15)
    documento.cell(
        largura, 8, _latin1("Certificamos que"), align="C", new_x="LMARGIN", new_y="NEXT"
    )
    documento.ln(3)
    documento.set_font("Helvetica", "B", 24)
    documento.cell(
        largura, 12, _latin1(certificado.nome_aluno or ""), align="C", new_x="LMARGIN", new_y="NEXT"
    )
    documento.ln(4)
    documento.set_font("Helvetica", "", 15)
    carga = (
        f", com carga horária de {certificado.carga_horaria} horas"
        if certificado.carga_horaria
        else ""
    )
    texto = (
        f"concluiu a trilha {certificado.nome_trilha}, da disciplina "
        f"{certificado.disciplina}{carga}, no Algorise."
    )
    documento.multi_cell(largura, 8, _latin1(texto), align="C", new_x="LMARGIN", new_y="NEXT")
    documento.ln(8)
    emitido = certificado.emitido_em.strftime("%d/%m/%Y") if certificado.emitido_em else ""
    documento.cell(
        largura,
        8,
        _latin1(f"Emitido em {emitido} por {certificado.parceiro}."),
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    documento.set_y(documento.h - 42)
    documento.set_font("Helvetica", "", 11)
    documento.cell(
        largura,
        6,
        _latin1(f"Código de validação: {certificado.codigo}"),
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    documento.cell(
        largura,
        6,
        _latin1("Confira a autenticidade em algorise, na página de validação de certificados."),
        align="C",
    )
    return bytes(documento.output())


def _concluidos(db: Session, usuario_id: int, trilha_id: int) -> int:
    return (
        db.scalar(
            select(func.count(ProgressoUsuario.id)).where(
                ProgressoUsuario.usuario_id == usuario_id,
                ProgressoUsuario.trilha_id == trilha_id,
                ProgressoUsuario.status == StatusProgresso.concluido,
            )
        )
        or 0
    )


def _codigo_livre(db: Session) -> str:
    while True:
        meio = "".join(secrets.choice(_ALFABETO) for _ in range(8))
        codigo = f"ALG-{meio[:4]}-{meio[4:]}"
        if db.scalar(select(Certificado.id).where(Certificado.codigo == codigo)) is None:
            return codigo


def _latin1(texto: str) -> str:
    """As fontes embutidas do PDF são latin-1: acento do português passa, emoji não."""
    return texto.encode("latin-1", "replace").decode("latin-1")
