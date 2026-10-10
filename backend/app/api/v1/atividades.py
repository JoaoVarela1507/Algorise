"""Atividades e submissões (telas 28 a 38).

O acesso é checado pelo passo: uma atividade de passo bloqueado não pode ser
lida nem respondida. A regra de desbloqueio é a mesma de `/trilhas` — está em
`app/services/progresso.py`, e existe uma cópia só dela.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import UsuarioAtual
from app.core.database import get_db
from app.core.erros import ErroDeNegocio
from app.models import Atividade, Modulo, Trilha, Usuario
from app.schemas.submissao import Correcao, Submissao, Tentativa
from app.schemas.trilha import AtividadeResumo
from app.services import progresso, submissoes

router = APIRouter(prefix="/atividades", tags=["atividades"])


@router.get(
    "/{atividade_id}",
    response_model=AtividadeResumo,
    summary="Enunciado da atividade",
    description="Nunca inclui o gabarito: a correção é do servidor (`POST .../submissoes`).",
)
def obter_atividade(
    atividade_id: int, usuario: UsuarioAtual, db: Session = Depends(get_db)
) -> AtividadeResumo:
    atividade, _, _ = _atividade_liberada(db, atividade_id, usuario)
    return AtividadeResumo.model_validate(atividade)


@router.post(
    "/{atividade_id}/submissoes",
    response_model=Correcao,
    status_code=status.HTTP_201_CREATED,
    summary="Envia a resposta e recebe a correção",
)
def submeter(
    atividade_id: int,
    dados: Submissao,
    usuario: UsuarioAtual,
    db: Session = Depends(get_db),
) -> Correcao:
    atividade, _, trilha = _atividade_liberada(db, atividade_id, usuario)

    try:
        tentativa, correcao, ganho = submissoes.submeter(
            db,
            usuario=usuario,
            atividade=atividade,
            trilha_id=trilha.id,
            conteudo=dados.conteudo,
            tempo_gasto_segundos=dados.tempo_gasto_segundos,
        )
    except submissoes.TipoNaoSuportado as erro:
        raise ErroDeNegocio(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="tipo_sem_correcao",
            message="Esse tipo de atividade ainda não tem correção automática",
            details={"tipo": atividade.tipo.value},
        ) from erro

    db.refresh(usuario)
    return Correcao(
        correta=correcao.correta,
        em_analise=correcao.em_analise,
        feedback=correcao.feedback,
        tentativa=tentativa.tentativa,
        xp_ganho=ganho,
        xp_total=usuario.xp_total,
    )


@router.get(
    "/{atividade_id}/submissoes",
    response_model=list[Tentativa],
    summary="Tentativas anteriores do aluno",
    description="Só as do próprio aluno; serve para retomar de onde parou.",
)
def listar_submissoes(
    atividade_id: int, usuario: UsuarioAtual, db: Session = Depends(get_db)
) -> list[Tentativa]:
    _atividade_liberada(db, atividade_id, usuario)
    return [
        Tentativa.model_validate(tentativa)
        for tentativa in submissoes.tentativas(db, usuario_id=usuario.id, atividade_id=atividade_id)
    ]


def _atividade_liberada(
    db: Session, atividade_id: int, usuario: Usuario
) -> tuple[Atividade, Modulo, Trilha]:
    """A atividade, o passo e a trilha — se o aluno já desbloqueou o passo."""
    atividade = db.execute(
        select(Atividade)
        .where(Atividade.id == atividade_id)
        .options(
            selectinload(Atividade.modulo).selectinload(Modulo.trilha).selectinload(Trilha.modulos)
        )
    ).scalar_one_or_none()

    if atividade is None or not atividade.modulo.trilha.publicada:
        raise ErroDeNegocio(
            status_code=status.HTTP_404_NOT_FOUND,
            code="atividade_nao_encontrada",
            message="Atividade não encontrada",
            details={"atividade_id": atividade_id},
        )

    modulo = atividade.modulo
    trilha = modulo.trilha

    try:
        progresso.conteudo_do_passo(db, usuario_id=usuario.id, trilha=trilha, ordem=modulo.ordem)
    except progresso.PassoBloqueado as erro:
        raise ErroDeNegocio(
            status_code=status.HTTP_403_FORBIDDEN,
            code="passo_bloqueado",
            message="Conclua o passo anterior para abrir esta atividade",
            details={"trilha": trilha.slug, "ordem": modulo.ordem},
        ) from erro

    return atividade, modulo, trilha
