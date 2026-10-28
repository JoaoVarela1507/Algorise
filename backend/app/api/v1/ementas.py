"""Upload da ementa em PDF (telas 14 e 15), a leitura dos assuntos e a revisão (#38)."""

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, Response, UploadFile, status
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import UsuarioAtual
from app.core.config import settings
from app.core.database import get_db, get_fabrica_de_sessoes
from app.core.erros import ErroDeNegocio
from app.ia import IAIndisponivel, ProvedorIA, get_provedor_ia
from app.ia.skills import ler_ementa
from app.models import Ementa, StatusAssuntos, Usuario
from app.schemas.academico import (
    AssuntoLido,
    AssuntosDaEmenta,
    AssuntosRevisados,
    DisciplinaLida,
    EmentaStatus,
    ModuloDoAssunto,
)
from app.services import assuntos_ementa, ementas

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ementas", tags=["ementas"])


@router.post(
    "",
    response_model=EmentaStatus,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Envia a ementa em PDF",
    description=(
        "Responde na hora com status `pendente`; o texto é extraído em segundo plano, "
        "e depois a IA lê as disciplinas e os assuntos (`status_assuntos`). "
        "Acompanhe por `GET /ementas/{id}`."
    ),
)
def enviar_ementa(
    usuario: UsuarioAtual,
    tarefas: BackgroundTasks,
    resposta: Response,
    arquivo: UploadFile = File(description="PDF de até 5 MB"),
    db: Session = Depends(get_db),
    fabrica: sessionmaker[Session] = Depends(get_fabrica_de_sessoes),
    provedor: ProvedorIA = Depends(get_provedor_ia),
) -> EmentaStatus:
    # Um byte além do limite basta para saber que passou, sem ler o resto.
    conteudo = arquivo.file.read(settings.tamanho_maximo_ementa + 1)
    try:
        ementa = ementas.receber(db, usuario, conteudo, arquivo.filename)
    except ementas.EmentaGrandeDemais as erro:
        megabytes = settings.tamanho_maximo_ementa // (1024 * 1024)
        raise ErroDeNegocio(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            code="ementa_grande_demais",
            message=f"A ementa pode ter até {megabytes} MB.",
            details={"limite_bytes": settings.tamanho_maximo_ementa},
        ) from erro
    except ementas.EmentaInvalida as erro:
        raise ErroDeNegocio(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            code="ementa_invalida",
            message=str(erro),
        ) from erro

    # O mesmo PDF enviado antes já tem o texto: falta só ler os assuntos.
    if ementas.precisa_processar(ementa):
        tarefas.add_task(ementas.processar, fabrica, provedor, ementa.id)

    resposta.headers["Location"] = f"/api/v1/ementas/{ementa.id}"
    return EmentaStatus.model_validate(ementa)


# Antes de `/{ementa_id}`: senão "atual" cairia ali e voltaria 422 por não ser número.
@router.get("/atual", response_model=EmentaStatus, summary="A última ementa enviada pelo aluno")
def obter_atual(usuario: UsuarioAtual, db: Session = Depends(get_db)) -> EmentaStatus:
    ementa = ementas.atual_do_aluno(db, usuario)
    if ementa is None:
        raise ErroDeNegocio(
            status_code=status.HTTP_404_NOT_FOUND,
            code="ementa_nao_encontrada",
            message="Você ainda não enviou uma ementa",
        )
    return EmentaStatus.model_validate(ementa)


@router.get("/{ementa_id}", response_model=EmentaStatus, summary="Status da leitura da ementa")
def obter_ementa(
    ementa_id: int, usuario: UsuarioAtual, db: Session = Depends(get_db)
) -> EmentaStatus:
    return EmentaStatus.model_validate(_do_aluno(db, usuario, ementa_id))


@router.get(
    "/{ementa_id}/assuntos",
    response_model=AssuntosDaEmenta,
    summary="Disciplinas e assuntos lidos da ementa",
    description=(
        "Cada assunto vem `coberto`, com o módulo do catálogo que o cobre, ou como "
        "`lacuna`, com o status da busca de conteúdo. A lista fica vazia até "
        "`status_assuntos` chegar a `prontos`."
    ),
)
def obter_assuntos(
    ementa_id: int, usuario: UsuarioAtual, db: Session = Depends(get_db)
) -> AssuntosDaEmenta:
    return _assuntos(_do_aluno(db, usuario, ementa_id))


@router.put(
    "/{ementa_id}/assuntos",
    response_model=AssuntosDaEmenta,
    summary="Grava a revisão dos assuntos",
    description=(
        "A lista inteira, como o aluno deixou: o que sai dela é removido. Só o assunto "
        "novo ou renomeado é buscado de novo no catálogo. 409 se os assuntos não estão "
        "`prontos`; 503 se a busca precisar da IA e ela estiver fora."
    ),
)
def revisar_assuntos(
    ementa_id: int,
    dados: AssuntosRevisados,
    usuario: UsuarioAtual,
    db: Session = Depends(get_db),
    provedor: ProvedorIA = Depends(get_provedor_ia),
) -> AssuntosDaEmenta:
    ementa = _do_aluno(db, usuario, ementa_id)
    if ementa.status_assuntos is not StatusAssuntos.prontos:
        raise _assuntos_indisponiveis(ementa)
    disciplinas = [ler_ementa.Disciplina(**d.model_dump()) for d in dados.disciplinas]
    try:
        # Rota síncrona roda numa thread, sem event loop.
        asyncio.run(assuntos_ementa.revisar(db, provedor, ementa, disciplinas))
    except IAIndisponivel as erro:
        logger.warning("IA indisponível na revisão da ementa %s: %s", ementa_id, erro)
        raise ErroDeNegocio(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="ia_indisponivel",
            message=assuntos_ementa.ERRO_IA_FORA,
        ) from erro
    return _assuntos(ementa)


@router.post(
    "/{ementa_id}/confirmar",
    response_model=EmentaStatus,
    summary="Confirma os assuntos e gera a trilha guiada",
    description=(
        "A ementa confirmada por último é a base de `GET /trilha-guiada`. "
        "409 se os assuntos não estão `prontos`."
    ),
)
def confirmar_ementa(
    ementa_id: int, usuario: UsuarioAtual, db: Session = Depends(get_db)
) -> EmentaStatus:
    ementa = _do_aluno(db, usuario, ementa_id)
    if not assuntos_ementa.confirmar(db, ementa):
        raise _assuntos_indisponiveis(ementa)
    return EmentaStatus.model_validate(ementa)


def _assuntos(ementa: Ementa) -> AssuntosDaEmenta:
    prontos = ementa.status_assuntos is StatusAssuntos.prontos
    return AssuntosDaEmenta(
        status_assuntos=ementa.status_assuntos,
        erro_assuntos=ementa.erro_assuntos,
        disciplinas=[
            DisciplinaLida(
                nome=disciplina.nome,
                periodo=disciplina.periodo,
                carga_horaria=disciplina.carga_horaria,
                assuntos=[
                    AssuntoLido(
                        texto=assunto.texto,
                        situacao="coberto" if assunto.modulo is not None else "lacuna",
                        modulo=ModuloDoAssunto.model_validate(assunto.modulo)
                        if assunto.modulo is not None
                        else None,
                        status_lacuna=assunto.lacuna.status if assunto.lacuna else None,
                    )
                    for assunto in disciplina.assuntos
                ],
            )
            for disciplina in (ementa.disciplinas if prontos else [])
        ],
    )


@router.post(
    "/{ementa_id}/assuntos",
    response_model=EmentaStatus,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Lê os assuntos da ementa de novo",
    description=(
        "Para quando a leitura falhou (a IA estava fora do ar) ou o catálogo cresceu. "
        "Só depois do texto extraído e fora de uma leitura em andamento; senão, 409."
    ),
)
def reler_assuntos(
    ementa_id: int,
    usuario: UsuarioAtual,
    tarefas: BackgroundTasks,
    db: Session = Depends(get_db),
    fabrica: sessionmaker[Session] = Depends(get_fabrica_de_sessoes),
    provedor: ProvedorIA = Depends(get_provedor_ia),
) -> EmentaStatus:
    ementa = _do_aluno(db, usuario, ementa_id)
    if not ementas.reler_assuntos(db, ementa):
        raise _assuntos_indisponiveis(ementa)
    tarefas.add_task(ementas.processar, fabrica, provedor, ementa.id)
    return EmentaStatus.model_validate(ementa)


def _assuntos_indisponiveis(ementa: Ementa) -> ErroDeNegocio:
    return ErroDeNegocio(
        status_code=status.HTTP_409_CONFLICT,
        code="assuntos_indisponiveis",
        message="Os assuntos desta ementa ainda não estão prontos. Aguarde a leitura.",
        details={"status": ementa.status, "status_assuntos": ementa.status_assuntos},
    )


def _do_aluno(db: Session, usuario: Usuario, ementa_id: int) -> Ementa:
    ementa = ementas.obter_do_aluno(db, usuario, ementa_id)
    if ementa is None:
        # A de outro aluno responde igual à inexistente: nem confirmar que ela
        # existe é da conta de quem pergunta.
        raise ErroDeNegocio(
            status_code=status.HTTP_404_NOT_FOUND,
            code="ementa_nao_encontrada",
            message="Ementa não encontrada",
            details={"ementa_id": ementa_id},
        )
    return ementa
