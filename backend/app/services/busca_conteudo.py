"""Vídeos do YouTube para as lacunas das ementas, com prioridade para playlists (#207).

Para cada disciplina com lacunas pendentes:

1. **Playlists primeiro.** Uma playlist traz a ordem das aulas, definida pelo
   professor, aulas curtas de um assunto só, um estilo coerente, e costuma
   cobrir várias lacunas de uma vez. Das candidatas, fica a que cobre mais
   lacunas, comparando o título de cada aula com cada assunto pelo embedding,
   **antes de baixar qualquer coisa**. Uma busca custa 100 unidades da cota; a
   lista de uma playlist, 1.
2. **Vídeos avulsos** para o que nenhuma playlist cobriu, um por lacuna, dentro
   da duração aceita.
3. A lacuna coberta passa para `em_preparacao`, com o vídeo ligado a ela; a que
   não achou nada, para `sem_conteudo`, sem nova tentativa automática.

O vídeo escolhido fica em `aguardando`, à espera da transcrição (#208).
"""

import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ia import ProvedorIA
from app.ia.skills.ler_ementa import normalizar
from app.ia.vault.busca import distancia_cosseno
from app.ia.vault.ingestao import LOTE_DE_EMBEDDING
from app.models import Lacuna, StatusLacuna, VideoLacuna, VideoYoutube
from app.services.youtube import ClienteYoutube, CotaEsgotada, Video

logger = logging.getLogger(__name__)

# Quantas playlists e quantos vídeos avulsos cada busca traz para comparar.
PLAYLISTS_POR_BUSCA = 5
VIDEOS_POR_BUSCA = 5


@dataclass
class Resultado:
    playlist_id: str | None = None
    videos: list[VideoYoutube] = field(default_factory=list)
    cobertas: int = 0
    sem_conteudo: int = 0
    # A cota acabou no meio: as lacunas que sobraram continuam `pendente`.
    interrompida: bool = False


async def buscar(
    db: Session, cliente: ClienteYoutube, provedor: ProvedorIA, disciplina: str
) -> Resultado:
    """Procura vídeos para as lacunas pendentes da disciplina e liga os que servem."""
    resultado = Resultado()
    lacunas = pendentes(db, disciplina)
    if not lacunas:
        return resultado
    vetores = await _vetores(provedor, [f"{disciplina}: {lacuna.assunto}" for lacuna in lacunas])
    restantes = dict(zip((lacuna.id for lacuna in lacunas), vetores, strict=True))
    por_id = {lacuna.id: lacuna for lacuna in lacunas}

    try:
        await _pela_playlist(db, cliente, provedor, disciplina, por_id, restantes, resultado)
        for lacuna_id in list(restantes):
            lacuna = por_id[lacuna_id]
            achado = await _avulso(cliente, provedor, disciplina, lacuna, restantes[lacuna_id])
            if achado is None:
                lacuna.status = StatusLacuna.sem_conteudo
                resultado.sem_conteudo += 1
            else:
                _ligar(db, lacuna, *achado, resultado)
            del restantes[lacuna_id]
    except CotaEsgotada as erro:
        logger.warning("Busca de %s parou: %s", disciplina, erro)
        resultado.interrompida = True
    db.commit()
    return resultado


def pendentes(db: Session, disciplina: str) -> list[Lacuna]:
    """As lacunas da disciplina que ainda esperam busca, sem contar acento e caixa."""
    alvo = normalizar(disciplina)
    return [
        lacuna
        for lacuna in db.scalars(
            select(Lacuna).where(Lacuna.status == StatusLacuna.pendente).order_by(Lacuna.id)
        )
        if normalizar(lacuna.disciplina) == alvo
    ]


async def _pela_playlist(
    db: Session,
    cliente: ClienteYoutube,
    provedor: ProvedorIA,
    disciplina: str,
    por_id: dict[int, Lacuna],
    restantes: dict[int, list[float]],
    resultado: Resultado,
) -> None:
    melhor: tuple[str, dict[int, tuple[Video, float]]] | None = None
    for playlist in cliente.playlists(f"{disciplina} aulas", maximo=PLAYLISTS_POR_BUSCA):
        aulas = cliente.itens_da_playlist(playlist.id)
        if not aulas:
            continue
        cobertura = _cobertura(
            restantes, aulas, await _vetores(provedor, [_texto(v) for v in aulas])
        )
        # Empate: a primeira, que é a mais relevante para a API.
        if cobertura and (melhor is None or len(cobertura) > len(melhor[1])):
            melhor = (playlist.id, cobertura)
    if melhor is None:
        return

    playlist_id, cobertura = melhor
    duracoes = cliente.duracoes([video.id for video, _ in cobertura.values()])
    for lacuna_id, (video, distancia) in cobertura.items():
        # Uma aula de playlist longa demais (a gravação de um dia inteiro) não
        # entra: a lacuna tenta um vídeo avulso.
        duracao = duracoes.get(video.id)
        if duracao is None or duracao > settings.youtube_duracao_maxima:
            continue
        _ligar(db, por_id[lacuna_id], video, duracao, distancia, resultado)
        del restantes[lacuna_id]
    resultado.playlist_id = playlist_id


async def _avulso(
    cliente: ClienteYoutube,
    provedor: ProvedorIA,
    disciplina: str,
    lacuna: Lacuna,
    vetor: list[float],
) -> tuple[Video, int, float] | None:
    candidatos = cliente.videos(f"{disciplina} {lacuna.assunto}", maximo=VIDEOS_POR_BUSCA)
    duracoes = cliente.duracoes([video.id for video in candidatos])
    aceitos = [
        video
        for video in candidatos
        if settings.youtube_duracao_minima
        <= duracoes.get(video.id, -1)
        <= settings.youtube_duracao_maxima
    ]
    if not aceitos:
        return None
    vetores = await _vetores(provedor, [_texto(video) for video in aceitos])
    distancia, video = min(
        ((distancia_cosseno(vetor, v), video) for video, v in zip(aceitos, vetores, strict=True)),
        key=lambda par: par[0],
    )
    if distancia > settings.youtube_distancia_maxima:
        return None
    return video, duracoes[video.id], distancia


def _cobertura(
    restantes: dict[int, list[float]], aulas: list[Video], vetores: list[list[float]]
) -> dict[int, tuple[Video, float]]:
    """Para cada lacuna, a aula mais próxima, se ela for perto o bastante."""
    cobertura = {}
    for lacuna_id, vetor in restantes.items():
        distancia, aula = min(
            ((distancia_cosseno(vetor, v), aula) for aula, v in zip(aulas, vetores, strict=True)),
            key=lambda par: par[0],
        )
        if distancia <= settings.youtube_distancia_maxima:
            cobertura[lacuna_id] = (aula, distancia)
    return cobertura


def _ligar(
    db: Session,
    lacuna: Lacuna,
    video: Video,
    duracao: int,
    distancia: float,
    resultado: Resultado,
) -> None:
    registro = db.scalar(select(VideoYoutube).where(VideoYoutube.youtube_id == video.id))
    if registro is None:
        registro = VideoYoutube(
            youtube_id=video.id,
            titulo=video.titulo[:300],
            canal=(video.canal or "")[:200] or None,
            duracao_segundos=duracao,
            playlist_id=video.playlist_id,
            posicao=video.posicao,
        )
        db.add(registro)
        resultado.videos.append(registro)
    if not any(ligacao.lacuna_id == lacuna.id for ligacao in registro.lacunas):
        registro.lacunas.append(VideoLacuna(lacuna=lacuna, distancia=distancia))
    lacuna.status = StatusLacuna.em_preparacao
    resultado.cobertas += 1


def _texto(video: Video) -> str:
    # O título diz o assunto; o começo da descrição ajuda quando ele é só "Aula 7".
    return f"{video.titulo}. {video.descricao[:200]}"


async def _vetores(provedor: ProvedorIA, textos: list[str]) -> list[list[float]]:
    vetores: list[list[float]] = []
    for inicio in range(0, len(textos), LOTE_DE_EMBEDDING):
        vetores.extend(await provedor.embeddings(textos[inicio : inicio + LOTE_DE_EMBEDDING]))
    return vetores
