"""As partes de vídeo aprovadas viram módulos da trilha, e as lacunas fecham (#210).

O módulo automático é publicado direto, sem aprovação de ninguém: a
categorização (#202) já é o controle de qualidade, e os alunos reportam o que
escapar. Ele entra na trilha da disciplina da parte, depois dos módulos que já
estão lá, na ordem das partes do vídeo; a trilha que não existe é criada.

Com reportes de `REPORTES_PARA_REMOVER` alunos, o módulo sai da trilha, as
lacunas que ele cobria voltam para `pendente` e a busca procura outro vídeo,
sem escolher este de novo.
"""

import logging
import re

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ia.skills.ler_ementa import normalizar
from app.models import (
    Lacuna,
    Modulo,
    OrigemModulo,
    ReporteModulo,
    StatusLacuna,
    Trilha,
    Usuario,
    VideoLacuna,
    VideoYoutube,
)
from app.services import trilhas

logger = logging.getLogger(__name__)


class SoModuloAutomatico(Exception):
    """Só o módulo feito de um vídeo do YouTube pode ser reportado."""


def publicar(db: Session, video: VideoYoutube) -> list[Modulo]:
    """Um módulo para cada parte aprovada do vídeo que ainda não virou módulo."""
    novos = []
    for parte in video.partes:
        if not parte.aprovada or parte.disciplina is None:
            continue
        if db.scalar(select(Modulo).where(Modulo.parte_video_id == parte.id)) is not None:
            continue
        trilha = trilha_da_disciplina(db, parte.disciplina)
        modulo = Modulo(
            trilha=trilha,
            ordem=_proxima_ordem(db, trilha),
            titulo=parte.titulo[:200],
            descricao=parte.resumo,
            video_url=f"https://www.youtube.com/watch?v={video.youtube_id}",
            inicio_segundos=parte.inicio_segundos,
            fim_segundos=parte.fim_segundos,
            origem=OrigemModulo.youtube,
            parte_video=parte,
        )
        db.add(modulo)
        db.flush()
        for lacuna in parte.lacunas:
            lacuna.status = StatusLacuna.coberta
            lacuna.modulo = modulo
        novos.append(modulo)
    db.commit()
    if novos:
        # O catálogo em cache não tem os módulos novos.
        trilhas.invalidar_catalogo()
        logger.info("Vídeo %s: %d módulos publicados", video.youtube_id, len(novos))
    return novos


def trilha_da_disciplina(db: Session, disciplina: str) -> Trilha:
    """A trilha da disciplina (sem contar acento e caixa), criada se não houver."""
    alvo = normalizar(disciplina)
    candidatas = [
        t
        for t in db.scalars(select(Trilha).order_by(Trilha.id))
        if normalizar(t.disciplina) == alvo
    ]
    if candidatas:
        # A publicada primeiro: é a que o aluno vê no catálogo.
        return next((t for t in candidatas if t.publicada), candidatas[0])
    trilha = Trilha(
        slug=_slug_livre(db, disciplina),
        nome=disciplina[:200],
        disciplina=disciplina[:200],
        descricao="Trilha montada com aulas gratuitas do YouTube.",
        publicada=True,
    )
    db.add(trilha)
    db.flush()
    return trilha


def reportar(db: Session, usuario: Usuario, modulo: Modulo) -> tuple[int, bool]:
    """Registra o reporte do aluno. Devolve o total de reportes e se o módulo saiu."""
    if modulo.origem is not OrigemModulo.youtube:
        raise SoModuloAutomatico
    try:
        with db.begin_nested():
            db.add(ReporteModulo(modulo_id=modulo.id, usuario_id=usuario.id))
    except IntegrityError:
        # O mesmo aluno de novo: não conta duas vezes.
        pass
    total = db.scalar(
        select(func.count()).select_from(ReporteModulo).where(ReporteModulo.modulo_id == modulo.id)
    )
    if total < settings.reportes_para_remover:
        db.commit()
        return total, False
    disciplinas = remover(db, modulo)
    _buscar_de_novo(disciplinas)
    return total, True


def remover(db: Session, modulo: Modulo) -> set[str]:
    """Tira o módulo da trilha e devolve as lacunas dele para a busca.

    Devolve as disciplinas que voltam para a busca. Os passos seguintes da
    trilha sobem uma posição: o "próximo passo" é a ordem mais um.
    """
    parte = modulo.parte_video
    lacunas = list(db.scalars(select(Lacuna).where(Lacuna.modulo_id == modulo.id)))
    for lacuna in lacunas:
        lacuna.status = StatusLacuna.pendente
        lacuna.modulo = None
    if parte is not None:
        # Não volta a ser publicada, e a busca não escolhe o vídeo de novo.
        parte.aprovada = False
        for ligacao in db.scalars(
            select(VideoLacuna).where(
                VideoLacuna.video_id == parte.video_id,
                VideoLacuna.lacuna_id.in_([lacuna.id for lacuna in lacunas]),
            )
        ):
            ligacao.recusada = True

    trilha, ordem = modulo.trilha, modulo.ordem
    db.delete(modulo)
    db.flush()
    for seguinte in sorted(
        (m for m in trilha.modulos if m.ordem > ordem and m is not modulo), key=lambda m: m.ordem
    ):
        seguinte.ordem -= 1
        db.flush()
    db.commit()
    trilhas.invalidar_catalogo()
    logger.info("Módulo %s removido por reportes", modulo.id)
    return {lacuna.disciplina for lacuna in lacunas}


def _buscar_de_novo(disciplinas: set[str]) -> None:
    from app.core.fila import fila_das_tarefas

    for disciplina in sorted(disciplinas):
        try:
            fila_das_tarefas().busca_de_conteudo(disciplina)
        except Exception:
            logger.exception("Não deu para enfileirar a busca de %s", disciplina)


def _proxima_ordem(db: Session, trilha: Trilha) -> int:
    ultima = db.scalar(select(func.max(Modulo.ordem)).where(Modulo.trilha_id == trilha.id))
    return (ultima or 0) + 1


def _slug_livre(db: Session, disciplina: str) -> str:
    base = re.sub(r"\s+", "-", normalizar(disciplina))[:100] or "trilha"
    slug, n = base, 2
    while db.scalar(select(Trilha.id).where(Trilha.slug == slug)) is not None:
        slug, n = f"{base}-{n}", n + 1
    return slug
