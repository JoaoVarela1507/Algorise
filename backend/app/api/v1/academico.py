"""Catálogo acadêmico do onboarding: autocomplete de instituição e curso (telas 14 e 15).

Público, como o catálogo de trilhas: são dados de instituições, não dos alunos.
Só aparece o que é verificado (ver `app/services/catalogo.py`).
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.erros import ErroDeNegocio
from app.schemas.academico import CursoResumo, InstituicaoResumo, PeriodoCurso
from app.services import catalogo

router = APIRouter(tags=["academico"])


@router.get(
    "/instituicoes",
    response_model=list[InstituicaoResumo],
    summary="Autocomplete de instituições",
    description="Tolera acento, caixa e erro de digitação. Casa com o nome ou a sigla.",
)
def buscar_instituicoes(
    busca: str = Query(default="", max_length=100),
    limite: int = Query(default=10, ge=1, le=20),
    db: Session = Depends(get_db),
) -> list[InstituicaoResumo]:
    return [
        InstituicaoResumo.model_validate(instituicao)
        for instituicao in catalogo.buscar_instituicoes(db, busca, limite=limite)
    ]


@router.get("/instituicoes/{instituicao_id}/cursos", response_model=list[CursoResumo])
def listar_cursos(instituicao_id: int, db: Session = Depends(get_db)) -> list[CursoResumo]:
    if catalogo.obter_instituicao_verificada(db, instituicao_id) is None:
        raise ErroDeNegocio(
            status_code=status.HTTP_404_NOT_FOUND,
            code="instituicao_nao_encontrada",
            message="Instituição não encontrada",
            details={"instituicao_id": instituicao_id},
        )
    return [
        CursoResumo.model_validate(curso)
        for curso in catalogo.cursos_da_instituicao(db, instituicao_id)
    ]


@router.get(
    "/cursos/{curso_id}/periodos",
    response_model=list[PeriodoCurso],
    summary="Períodos do curso e as disciplinas que o Algorise cobre em cada um",
)
def listar_periodos(curso_id: int, db: Session = Depends(get_db)) -> list[PeriodoCurso]:
    curso = catalogo.obter_curso_verificado(db, curso_id)
    if curso is None:
        raise ErroDeNegocio(
            status_code=status.HTTP_404_NOT_FOUND,
            code="curso_nao_encontrado",
            message="Curso não encontrado",
            details={"curso_id": curso_id},
        )
    return [
        PeriodoCurso(numero=periodo.numero, disciplinas=periodo.disciplinas)
        for periodo in catalogo.periodos_do_curso(db, curso)
    ]
