"""Certificados do aluno (tela 20), o PDF e a validação pública (#32)."""

from itertools import groupby

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import UsuarioAtual
from app.core.database import get_db
from app.core.erros import ErroDeNegocio
from app.schemas.certificado import (
    Certificado,
    ItemDeCertificado,
    PeriodoDeCertificados,
    Validacao,
)
from app.services import certificados as servico

router = APIRouter(prefix="/certificados", tags=["certificados"])


@router.get(
    "",
    response_model=list[PeriodoDeCertificados],
    summary="Certificados do aluno, agrupados por período",
    description=(
        "Só as trilhas de parceiros, que são as que emitem certificado. Cada uma vem "
        "`liberado`, com o id do certificado, ou `bloqueado`, com o progresso."
    ),
)
def listar_certificados(
    usuario: UsuarioAtual, db: Session = Depends(get_db)
) -> list[PeriodoDeCertificados]:
    itens = servico.listar(db, usuario)
    return [
        PeriodoDeCertificados(
            periodo=periodo,
            itens=[
                ItemDeCertificado(
                    trilha_id=item.trilha.id,
                    slug=item.trilha.slug,
                    nome=item.trilha.nome,
                    disciplina=item.trilha.disciplina,
                    parceiro=item.trilha.parceiro.nome,
                    carga_horaria=item.trilha.carga_horaria,
                    total_modulos=item.total_modulos,
                    concluidos=item.concluidos,
                    estado="liberado" if item.certificado else "bloqueado",
                    certificado_id=item.certificado.id if item.certificado else None,
                )
                for item in grupo
            ],
        )
        for periodo, grupo in groupby(itens, key=lambda item: item.trilha.periodo)
    ]


# Antes de `/{certificado_id}`: senão "validar" cairia lá e voltaria 422.
@router.get(
    "/validar/{codigo}",
    response_model=Validacao,
    summary="Valida um certificado pelo código, sem login",
    description="404 para código que não existe.",
)
def validar_certificado(codigo: str, db: Session = Depends(get_db)) -> Validacao:
    certificado = servico.validar(db, codigo)
    if certificado is None:
        raise ErroDeNegocio(
            status_code=status.HTTP_404_NOT_FOUND,
            code="certificado_invalido",
            message="Nenhum certificado com esse código",
        )
    return Validacao.model_validate(certificado, from_attributes=True)


@router.get("/{certificado_id}", response_model=Certificado, summary="Dados de um certificado")
def obter_certificado(
    certificado_id: int, usuario: UsuarioAtual, db: Session = Depends(get_db)
) -> Certificado:
    return Certificado.model_validate(_do_aluno(db, usuario, certificado_id))


@router.get(
    "/{certificado_id}/download",
    summary="PDF do certificado",
    description="Só o dono baixa; o de outro aluno, ou o não conquistado, responde 404.",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
def baixar_certificado(
    certificado_id: int, usuario: UsuarioAtual, db: Session = Depends(get_db)
) -> Response:
    certificado = _do_aluno(db, usuario, certificado_id)
    return Response(
        servico.pdf(certificado),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="certificado-{certificado.codigo}.pdf"'
        },
    )


def _do_aluno(db: Session, usuario, certificado_id: int):
    certificado = servico.do_aluno(db, usuario, certificado_id)
    if certificado is None:
        raise ErroDeNegocio(
            status_code=status.HTTP_404_NOT_FOUND,
            code="certificado_nao_encontrado",
            message="Certificado não encontrado",
            details={"certificado_id": certificado_id},
        )
    return certificado
