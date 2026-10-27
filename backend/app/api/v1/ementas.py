"""Upload da ementa em PDF (telas 14 e 15), o status da leitura e os assuntos lidos (#38)."""

from fastapi import APIRouter, BackgroundTasks, Depends, File, Response, UploadFile, status
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import UsuarioAtual
from app.core.config import settings
from app.core.database import get_db, get_fabrica_de_sessoes
from app.core.erros import ErroDeNegocio
from app.ia import ProvedorIA, get_provedor_ia
from app.models import Ementa, StatusAssuntos, Usuario
from app.schemas.academico import (
    AssuntoLido,
    AssuntosDaEmenta,
    DisciplinaLida,
    EmentaStatus,
    ModuloDoAssunto,
)
from app.services import ementas

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
    ementa = _do_aluno(db, usuario, ementa_id)
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
        raise ErroDeNegocio(
            status_code=status.HTTP_409_CONFLICT,
            code="assuntos_indisponiveis",
            message="A ementa ainda não pode ser lida de novo. Aguarde a leitura atual.",
            details={"status": ementa.status, "status_assuntos": ementa.status_assuntos},
        )
    tarefas.add_task(ementas.processar, fabrica, provedor, ementa.id)
    return EmentaStatus.model_validate(ementa)


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
