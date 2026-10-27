"""Upload da ementa em PDF (telas 14 e 15) e o status da leitura."""

from fastapi import APIRouter, BackgroundTasks, Depends, File, Response, UploadFile, status
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import UsuarioAtual
from app.core.config import settings
from app.core.database import get_db, get_fabrica_de_sessoes
from app.core.erros import ErroDeNegocio
from app.models import StatusEmenta
from app.schemas.academico import EmentaStatus
from app.services import ementas

router = APIRouter(prefix="/ementas", tags=["ementas"])


@router.post(
    "",
    response_model=EmentaStatus,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Envia a ementa em PDF",
    description=(
        "Responde na hora com status `pendente`; o texto é extraído em segundo plano. "
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

    # Já lida (o mesmo PDF foi enviado antes): não há o que processar.
    if ementa.status is StatusEmenta.pendente:
        tarefas.add_task(ementas.processar, fabrica, ementa.id)

    resposta.headers["Location"] = f"/api/v1/ementas/{ementa.id}"
    return EmentaStatus.model_validate(ementa)


@router.get("/{ementa_id}", response_model=EmentaStatus, summary="Status da leitura da ementa")
def obter_ementa(
    ementa_id: int, usuario: UsuarioAtual, db: Session = Depends(get_db)
) -> EmentaStatus:
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
    return EmentaStatus.model_validate(ementa)
