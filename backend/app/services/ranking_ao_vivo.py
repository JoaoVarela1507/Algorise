"""Ranking em tempo real (#37): `ranking.atualizado`, agregado e só com o delta.

Ganhar XP não publica nada na hora. `marcar` anota quem ganhou e em quais
rankings (`ranking:geral` e o da trilha da atividade) e pronto. A cada
`RANKING_INTERVALO_AO_VIVO` segundos, o `Agregador` de alguma instância da API
descarrega o que foi anotado, com um evento por ranking que mudou, por mais
pontos que tenham entrado no intervalo.

**Delta, não a lista.** Cada ranking guarda no Redis uma foto das posições do
topo (`LIMITE_DO_DELTA` primeiros). O evento leva só as linhas que mudaram de
posição ou de XP desde a última foto, mais as de quem ganhou XP, mesmo que fora
do topo:

    {"mudancas": [{"posicao", "usuario_id", "username", "nome_exibicao",
                   "avatar_url", "xp"}, ...], "total": 1234}

As anotações ficam no Redis porque o XP também é ganho no worker, e qualquer
instância com conexões abertas pode descarregar: o `SPOP` garante que cada
ranking sai uma vez só. Com o Redis fora, as anotações e as fotos ficam na
memória da instância, e só ela descarrega o que viu.
"""

import logging
import threading
from collections.abc import Callable
from typing import Any

from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import chave
from app.core.config import settings
from app.core.redis import executar
from app.models import Atividade, Modulo, OrigemXP, Trilha
from app.schemas.ranking import EntradaRanking
from app.services import ranking
from app.services.tempo_real import publicar

logger = logging.getLogger(__name__)

GERAL = "ranking:geral"
LIMITE_DO_DELTA = 200
# A foto some sozinha se ninguém ganhar XP por um dia: a próxima recomeça.
VALIDADE_DA_FOTO = 24 * 60 * 60

CHAVE_SUJOS = chave("ranking", "sujos")

_trava = threading.Lock()
_sujos_locais: dict[str, set[int]] = {}
_fotos_locais: dict[str, dict[str, str]] = {}


def canal_da_trilha(trilha_id: int) -> str:
    return f"ranking:{trilha_id}"


def marcar(db: Session, usuario_id: int, origem: OrigemXP, referencia_id: int | None) -> None:
    """Anota que o aluno ganhou XP. Chamado por `xp.registrar_xp`, depois do commit."""
    canais = [GERAL]
    trilha_id = trilha_de(db, origem, referencia_id)
    if trilha_id is not None:
        canais.append(canal_da_trilha(trilha_id))

    def anotar(r: Redis) -> bool:
        with r.pipeline() as pipe:
            for canal in canais:
                pipe.sadd(_chave_dos_ganhos(canal), usuario_id)
                pipe.sadd(CHAVE_SUJOS, canal)
            pipe.execute()
        return True

    if not executar(anotar, padrao=False):
        with _trava:
            for canal in canais:
                _sujos_locais.setdefault(canal, set()).add(usuario_id)


def trilha_de(db: Session, origem: OrigemXP, referencia_id: int | None) -> int | None:
    """A trilha de onde veio o XP, se ele veio de uma."""
    if referencia_id is None:
        return None
    if origem is OrigemXP.trilha:
        return referencia_id
    if origem is OrigemXP.modulo:
        return db.scalar(select(Modulo.trilha_id).where(Modulo.id == referencia_id))
    if origem is OrigemXP.atividade:
        return db.scalar(
            select(Modulo.trilha_id)
            .join(Atividade, Atividade.modulo_id == Modulo.id)
            .where(Atividade.id == referencia_id)
        )
    return None


def descarregar(db: Session) -> int:
    """Publica um `ranking.atualizado` por ranking anotado. Devolve quantos saíram."""
    publicados = 0
    for canal, ganhadores in _pegar_anotados().items():
        if _emitir(db, canal, ganhadores):
            publicados += 1
    return publicados


def _pegar_anotados() -> dict[str, set[int]]:
    with _trava:
        anotados = {canal: set(ids) for canal, ids in _sujos_locais.items()}
        _sujos_locais.clear()

    def pegar(r: Redis) -> dict[str, set[int]]:
        canais = r.spop(CHAVE_SUJOS, 100) or []
        do_redis: dict[str, set[int]] = {}
        for canal in canais:
            with r.pipeline() as pipe:
                pipe.smembers(_chave_dos_ganhos(canal))
                pipe.delete(_chave_dos_ganhos(canal))
                ids, _ = pipe.execute()
            do_redis[canal] = {int(i) for i in ids}
        return do_redis

    for canal, ids in (executar(pegar, padrao={}) or {}).items():
        anotados.setdefault(canal, set()).update(ids)
    return anotados


def _emitir(db: Session, canal: str, ganhadores: set[int]) -> bool:
    if canal == GERAL:
        topo = ranking.obter_ranking(db, limite=LIMITE_DO_DELTA, deslocamento=0)

        def posicao_de(usuario_id: int) -> EntradaRanking | None:
            return ranking.posicao_geral(db, usuario_id)
    else:
        trilha = db.get(Trilha, int(canal.split(":", 1)[1]))
        if trilha is None:
            return False
        topo = ranking.por_trilha(
            db, trilha, limite=LIMITE_DO_DELTA, deslocamento=0, usuario_id=None
        )

        def posicao_de(usuario_id: int) -> EntradaRanking | None:
            return ranking.por_trilha(
                db, trilha, limite=0, deslocamento=0, usuario_id=usuario_id
            ).usuario

    atuais = {entrada.usuario_id: entrada for entrada in topo.lista}
    foto_anterior = _ler_foto(canal)
    mudancas: dict[int, EntradaRanking] = {}
    if foto_anterior:
        for usuario_id, entrada in atuais.items():
            if foto_anterior.get(str(usuario_id)) != _resumo(entrada):
                mudancas[usuario_id] = entrada
    for usuario_id in ganhadores:
        entrada = atuais.get(usuario_id) or posicao_de(usuario_id)
        if entrada is not None:
            mudancas[usuario_id] = entrada
    _gravar_foto(canal, {str(i): _resumo(e) for i, e in atuais.items()})

    if not mudancas:
        return False
    payload: dict[str, Any] = {
        "mudancas": [
            e.model_dump(mode="json") for e in sorted(mudancas.values(), key=lambda e: e.posicao)
        ],
        "total": topo.total,
    }
    publicar(canal, "ranking.atualizado", payload)
    return True


def _resumo(entrada: EntradaRanking) -> str:
    return f"{entrada.posicao}:{entrada.xp}"


def _chave_dos_ganhos(canal: str) -> str:
    return chave("ranking", "ganhos", canal)


def _chave_da_foto(canal: str) -> str:
    return chave("ranking", "foto", canal)


def _ler_foto(canal: str) -> dict[str, str]:
    foto = executar(lambda r: r.hgetall(_chave_da_foto(canal)), padrao=None)
    if foto is None:
        with _trava:
            return dict(_fotos_locais.get(canal, {}))
    return foto


def _gravar_foto(canal: str, foto: dict[str, str]) -> None:
    def gravar(r: Redis) -> bool:
        with r.pipeline() as pipe:
            pipe.delete(_chave_da_foto(canal))
            if foto:
                pipe.hset(_chave_da_foto(canal), mapping=foto)
                pipe.expire(_chave_da_foto(canal), VALIDADE_DA_FOTO)
            pipe.execute()
        return True

    if not executar(gravar, padrao=False):
        with _trava:
            _fotos_locais[canal] = foto


class Agregador:
    """Thread que descarrega os rankings anotados a cada intervalo.

    Sobe com a primeira conexão de WebSocket da instância (`garantir`), como o
    ouvinte do pub/sub: uma instância sem ninguém conectado não precisa fazer isso.
    """

    def __init__(self) -> None:
        self._trava = threading.Lock()
        self._thread: threading.Thread | None = None
        self._parar = threading.Event()
        self._fabrica: Callable[[], Session] | None = None

    def garantir(self, fabrica: Callable[[], Session]) -> None:
        with self._trava:
            self._fabrica = fabrica
            if self._thread is not None and self._thread.is_alive():
                return
            self._parar.clear()
            self._thread = threading.Thread(target=self._rodar, name="ranking-ws", daemon=True)
            self._thread.start()

    def parar(self) -> None:
        with self._trava:
            self._parar.set()
            thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout=5)

    def _rodar(self) -> None:
        while not self._parar.wait(settings.ranking_intervalo_ao_vivo):
            fabrica = self._fabrica
            if fabrica is None:
                continue
            try:
                with fabrica() as db:
                    descarregar(db)
            except Exception:
                # Um ranking que falhou não pode parar os próximos intervalos.
                logger.exception("Falha ao publicar o ranking em tempo real")


agregador = Agregador()
