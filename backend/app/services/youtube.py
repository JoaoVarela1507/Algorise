"""Cliente da YouTube Data API v3, para a busca de conteúdo das lacunas (#207).

Três cuidados que a API pede:

- **cota:** o Google dá 10 mil unidades por dia, e uma busca (`search`) custa
  100. Cada chamada soma o custo num contador no Redis, zerado à meia-noite do
  Pacífico, como a cota do Google; passou de `YOUTUBE_COTA_DIARIA`, a chamada
  não sai (`CotaEsgotada`) e o resto fica para o dia seguinte;
- **cache:** a resposta de cada consulta fica em `buscas_youtube` por 30 dias.
  Duas ementas com a mesma lacuna não pagam a mesma busca duas vezes;
- **o que vem quebrado:** vídeo privado ou apagado aparece na playlist sem
  título de verdade e sem id, e é descartado aqui.
"""

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx2
from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import redis as nucleo_redis
from app.core.config import settings
from app.models import BuscaYoutube

logger = logging.getLogger(__name__)

API = "https://www.googleapis.com/youtube/v3"
# Unidades de cota por chamada, da documentação da API.
CUSTO = {"search": 100, "playlistItems": 1, "videos": 1}
VALIDADE_DO_CACHE = timedelta(days=30)
# A cota do Google vira à meia-noite do horário do Pacífico.
_FUSO_DA_COTA = ZoneInfo("America/Los_Angeles")
_DURACAO = re.compile(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$")
_SEM_CONTEUDO = {"Private video", "Deleted video"}


class CotaEsgotada(Exception):
    """A cota do dia acabou: o resto da busca fica para amanhã."""


class YoutubeIndisponivel(Exception):
    """A API não respondeu ou respondeu com erro. A mensagem é para o log."""


@dataclass(frozen=True)
class Playlist:
    id: str
    titulo: str
    canal: str | None


@dataclass(frozen=True)
class Video:
    id: str
    titulo: str
    descricao: str = ""
    canal: str | None = None
    playlist_id: str | None = None
    # A partir de 1, como o aluno vê na playlist.
    posicao: int | None = None


class ClienteYoutube:
    def __init__(
        self,
        db: Session,
        chave: str,
        *,
        cota_diaria: int | None = None,
        transport: httpx2.BaseTransport | None = None,
    ) -> None:
        self.db = db
        self.chave = chave
        self.cota_diaria = settings.youtube_cota_diaria if cota_diaria is None else cota_diaria
        # Injetado pelos testes (`httpx2.MockTransport`); em produção, a rede.
        self.transport = transport

    def playlists(self, consulta: str, *, maximo: int = 5) -> list[Playlist]:
        dados = self._get("search", _busca(consulta, "playlist", maximo))
        return [
            Playlist(
                id=item["id"]["playlistId"],
                titulo=item["snippet"]["title"],
                canal=item["snippet"].get("channelTitle"),
            )
            for item in dados.get("items", [])
            if item.get("id", {}).get("playlistId")
        ]

    def videos(self, consulta: str, *, maximo: int = 5) -> list[Video]:
        dados = self._get("search", _busca(consulta, "video", maximo))
        return [
            Video(
                id=item["id"]["videoId"],
                titulo=item["snippet"]["title"],
                descricao=item["snippet"].get("description", ""),
                canal=item["snippet"].get("channelTitle"),
            )
            for item in dados.get("items", [])
            if item.get("id", {}).get("videoId")
        ]

    def itens_da_playlist(self, playlist_id: str, *, maximo: int = 50) -> list[Video]:
        dados = self._get(
            "playlistItems",
            {"part": "snippet", "playlistId": playlist_id, "maxResults": str(min(maximo, 50))},
        )
        videos = []
        for item in dados.get("items", []):
            snippet = item.get("snippet", {})
            video_id = snippet.get("resourceId", {}).get("videoId")
            if not video_id or snippet.get("title") in _SEM_CONTEUDO:
                continue
            videos.append(
                Video(
                    id=video_id,
                    titulo=snippet["title"],
                    descricao=snippet.get("description", ""),
                    canal=snippet.get("videoOwnerChannelTitle") or snippet.get("channelTitle"),
                    playlist_id=playlist_id,
                    posicao=snippet.get("position", 0) + 1,
                )
            )
        return videos

    def duracoes(self, ids: list[str]) -> dict[str, int]:
        """A duração de cada vídeo, em segundos. Uma chamada a cada 50 ids."""
        duracoes: dict[str, int] = {}
        unicos = sorted(set(ids))
        for inicio in range(0, len(unicos), 50):
            lote = unicos[inicio : inicio + 50]
            dados = self._get("videos", {"part": "contentDetails", "id": ",".join(lote)})
            for item in dados.get("items", []):
                segundos = duracao_em_segundos(item.get("contentDetails", {}).get("duration", ""))
                if segundos is not None:
                    duracoes[item["id"]] = segundos
        return duracoes

    def _get(self, recurso: str, parametros: dict[str, str]) -> dict:
        chave = f"{recurso}?" + "&".join(f"{k}={v}" for k, v in sorted(parametros.items()))
        guardada = self.db.scalar(select(BuscaYoutube).where(BuscaYoutube.chave == chave))
        if guardada is not None and _ainda_vale(guardada):
            return guardada.resposta

        self._gastar(CUSTO[recurso])
        try:
            with httpx2.Client(base_url=API, timeout=15, transport=self.transport) as cliente:
                resposta = cliente.get(f"/{recurso}", params={**parametros, "key": self.chave})
        except httpx2.HTTPError as erro:
            raise YoutubeIndisponivel(f"Falha ao falar com a API do YouTube: {erro}") from erro
        if resposta.status_code == 403 and "quota" in resposta.text.lower():
            raise CotaEsgotada("A API do YouTube recusou por cota")
        if resposta.status_code != httpx2.codes.OK:
            raise YoutubeIndisponivel(
                f"A API do YouTube respondeu {resposta.status_code}: {resposta.text[:200]}"
            )

        dados = resposta.json()
        if guardada is None:
            self.db.add(BuscaYoutube(chave=chave, resposta=dados))
        else:
            guardada.resposta = dados
            guardada.atualizado_em = datetime.now(UTC)
        # A cota já foi gasta: a resposta fica guardada mesmo que a busca pare
        # depois, por cota ou erro.
        self.db.commit()
        return dados

    def _gastar(self, custo: int) -> None:
        dia = datetime.now(_FUSO_DA_COTA).date().isoformat()
        chave = f"algorise:youtube:cota:{dia}"

        def somar(r: Redis) -> int:
            gasto = int(r.incrby(chave, custo))
            r.expire(chave, 2 * 24 * 60 * 60)
            if gasto > self.cota_diaria:
                r.decrby(chave, custo)
            return gasto

        # Sem o Redis, sem contagem: o Google ainda recusa quando a cota acaba.
        gasto = nucleo_redis.executar(somar)
        if gasto is not None and gasto > self.cota_diaria:
            raise CotaEsgotada(f"A cota do dia ({self.cota_diaria} unidades) acabou")


def duracao_em_segundos(iso: str) -> int | None:
    """`PT1H2M3S` -> 3723. `None` para o que não é duração: a live em andamento vem `P0D`."""
    achou = _DURACAO.match(iso)
    if not achou:
        return None
    dias, horas, minutos, segundos = (int(g or 0) for g in achou.groups())
    return ((dias * 24 + horas) * 60 + minutos) * 60 + segundos or None


def _busca(consulta: str, tipo: str, maximo: int) -> dict[str, str]:
    return {
        "part": "snippet",
        "q": consulta,
        "type": tipo,
        "maxResults": str(maximo),
        "relevanceLanguage": "pt",
        "regionCode": "BR",
    }


def _ainda_vale(busca: BuscaYoutube) -> bool:
    quando = busca.atualizado_em
    if quando.tzinfo is None:
        # O SQLite dos testes devolve sem fuso.
        quando = quando.replace(tzinfo=UTC)
    return datetime.now(UTC) - quando < VALIDADE_DO_CACHE
