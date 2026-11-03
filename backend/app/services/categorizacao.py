"""De que matéria é cada parte de um vídeo, e que lacunas ela cobre (#202).

A skill `categorizar_videos` lê a transcrição da parte e escolhe entre as
matérias do catálogo (as disciplinas das trilhas e das lacunas ligadas ao
vídeo), ou responde "nenhuma". A parte com matéria e confiança acima de
`CATEGORIZACAO_CONFIANCA_MINIMA` é aprovada, com as lacunas que cobre; a outra é
descartada.

Uma lacuna que o vídeo deveria cobrir e que nenhuma parte aprovada cobre tem a
ligação recusada: ela volta para `pendente` (se nenhum outro vídeo estiver a
caminho) e a busca procura de novo, sem repetir este vídeo.
"""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ia import ProvedorIA
from app.ia.skills import categorizar_videos
from app.ia.skills.ler_ementa import normalizar
from app.models import DocumentoVault, Lacuna, StatusLacuna, Trilha, VideoLacuna, VideoYoutube

logger = logging.getLogger(__name__)

JUSTIFICATIVA_INVALIDA = "A IA não respondeu no formato pedido."


async def categorizar(db: Session, provedor: ProvedorIA, video: VideoYoutube) -> set[str]:
    """Categoriza as partes do vídeo. Devolve as disciplinas que voltam para a busca."""
    ligacoes = [ligacao for ligacao in video.lacunas if not ligacao.recusada]
    lacunas = [ligacao.lacuna for ligacao in ligacoes]
    assuntos = [lacuna.assunto for lacuna in lacunas]
    materias = materias_possiveis(db, lacunas)
    trechos = _trechos(db, video)

    for parte in video.partes:
        # Cada trecho conta para a parte em que termina: ele começa repetindo o
        # fim do anterior, e o começo pode cair na parte de antes.
        texto = " ".join(
            texto for fim, texto in trechos if parte.inicio_segundos < fim <= parte.fim_segundos
        )
        try:
            categoria = await _perguntar(provedor, texto, materias, assuntos)
        except categorizar_videos.SaidaInvalida:
            logger.warning(
                "Categorização inválida da parte %s do vídeo %s", parte.ordem, video.youtube_id
            )
            categoria = categorizar_videos.Categoria(None, [], 0.0, JUSTIFICATIVA_INVALIDA)
        parte.disciplina = categoria.materia
        parte.confianca = categoria.confianca
        parte.justificativa = categoria.justificativa or None
        parte.aprovada = (
            categoria.materia is not None
            and categoria.confianca >= settings.categorizacao_confianca_minima
        )
        parte.lacunas = [lacunas[i] for i in categoria.assuntos] if parte.aprovada else []

    cobertas = {lacuna.id for parte in video.partes if parte.aprovada for lacuna in parte.lacunas}
    de_volta: set[str] = set()
    for ligacao in ligacoes:
        if ligacao.lacuna_id in cobertas:
            continue
        ligacao.recusada = True
        lacuna = ligacao.lacuna
        # Outro vídeo ainda pode cobrir a lacuna: só volta para a busca sem nenhum.
        if lacuna.status is StatusLacuna.em_preparacao and not _outro_a_caminho(db, lacuna, video):
            lacuna.status = StatusLacuna.pendente
            de_volta.add(lacuna.disciplina)
    db.commit()
    return de_volta


def materias_possiveis(db: Session, lacunas: list[Lacuna]) -> list[str]:
    """As disciplinas das trilhas e das lacunas, uma vez cada, sem contar acento e caixa."""
    nomes = [
        *db.scalars(select(Trilha.disciplina).distinct()),
        *(lacuna.disciplina for lacuna in lacunas),
    ]
    unicas: dict[str, str] = {}
    for nome in nomes:
        unicas.setdefault(normalizar(nome), nome)
    return sorted(unicas.values())


async def _perguntar(
    provedor: ProvedorIA, texto: str, materias: list[str], assuntos: list[str]
) -> categorizar_videos.Categoria:
    pedacos = [
        pedaco
        async for pedaco in provedor.gerar(
            categorizar_videos.mensagens(texto, materias, assuntos),
            max_tokens=categorizar_videos.MAXIMO_DE_TOKENS,
            formato=categorizar_videos.FORMATO,
        )
    ]
    return categorizar_videos.ler_resposta("".join(pedacos), materias, len(assuntos))


def _outro_a_caminho(db: Session, lacuna: Lacuna, video: VideoYoutube) -> bool:
    """Outro vídeo, ainda não recusado, está ligado à lacuna."""
    outras = db.scalars(
        select(VideoLacuna).where(
            VideoLacuna.lacuna_id == lacuna.id,
            VideoLacuna.video_id != video.id,
            VideoLacuna.recusada.is_(False),
        )
    )
    return outras.first() is not None


def _trechos(db: Session, video: VideoYoutube) -> list[tuple[float, str]]:
    """O fim de cada trecho da transcrição do vídeo, com o texto."""
    documento = db.scalar(select(DocumentoVault).where(DocumentoVault.video_id == video.id))
    if documento is None:
        return []
    return [(t.fim_segundos or t.inicio_segundos or 0.0, t.texto) for t in documento.trechos]
