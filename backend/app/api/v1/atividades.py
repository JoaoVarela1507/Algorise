"""Atividades e submissões (telas 28 a 38).

O acesso é checado pelo passo: uma atividade de passo bloqueado não pode ser
lida nem respondida. A regra de desbloqueio é a mesma de `/trilhas` — está em
`app/services/progresso.py`, e existe uma cópia só dela.
"""

import logging

import anyio
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import UsuarioAtual
from app.core.database import get_db
from app.core.erros import ErroDeNegocio
from app.ia import IAIndisponivel, ProvedorIA, get_provedor_ia
from app.ia.skills import corrigir_resposta
from app.models import Atividade, Modulo, Trilha, Usuario
from app.schemas.submissao import Correcao, Submissao, Tentativa
from app.schemas.trilha import AtividadeResumo
from app.services import correcao_aberta, progresso, submissoes

logger = logging.getLogger(__name__)

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
    provedor: ProvedorIA = Depends(get_provedor_ia),
) -> Correcao:
    atividade, _, _ = _atividade_liberada(db, atividade_id, usuario)

    try:
        tentativa, correcao, ganho = submissoes.submeter(
            db,
            usuario=usuario,
            atividade=atividade,
            conteudo=dados.conteudo,
            tempo_gasto_segundos=dados.tempo_gasto_segundos,
            corretor_aberta=_corretor_com_ia(provedor),
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
        sugestao=correcao.sugestao,
        corrigida_por_ia=correcao.corrigida_por_ia,
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


def _corretor_com_ia(provedor: ProvedorIA) -> submissoes.CorretorAberta:
    """A correção da resposta aberta pela IA, para a rota síncrona.

    A rota roda numa thread do FastAPI; `anyio.from_thread.run` leva a chamada
    para o event loop da aplicação, onde o cliente HTTP do provedor já está
    aberto (o do Gemini é um por loop). Falhou, devolve `None`: a resposta fica
    em análise e o aluno segue.
    """

    def corrigir(atividade: Atividade, conteudo: str) -> submissoes.Correcao | None:
        try:
            veredito = anyio.from_thread.run(
                lambda: correcao_aberta.corrigir(
                    provedor,
                    enunciado=atividade.enunciado,
                    referencia=atividade.resposta_esperada or "",
                    resposta=conteudo,
                )
            )
        except (IAIndisponivel, corrigir_resposta.SaidaInvalida, TimeoutError) as erro:
            logger.warning("Correção da atividade %s pela IA falhou: %s", atividade.id, erro)
            return None
        return submissoes.Correcao(
            correta=veredito.correta,
            em_analise=False,
            feedback=veredito.feedback,
            sugestao=veredito.faltou or None,
            corrigida_por_ia=True,
        )

    return corrigir


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
        progresso.conteudo_do_passo(db, usuario=usuario, trilha=trilha, ordem=modulo.ordem)
    except progresso.PassoBloqueado as erro:
        raise ErroDeNegocio(
            status_code=status.HTTP_403_FORBIDDEN,
            code="passo_bloqueado",
            message="Conclua o passo anterior para abrir esta atividade",
            details={"trilha": trilha.slug, "ordem": modulo.ordem},
        ) from erro

    return atividade, modulo, trilha
