"""Ranking de XP servido de um sorted set do Redis.

O sorted set guarda `usuario_id -> xp`: pódio, página da lista rolável e posição
do aluno saem dele em O(log n), sem ordenar a tabela de usuários a cada abertura
de tela. Quem grava XP mantém o score em dia (`app/services/xp.py`), então a
invalidação é explícita e o TTL é só a rede de segurança.

Nome e avatar continuam vindo do banco: mudam sem passar por XP, e a consulta é
um `id IN (...)` dos poucos alunos que a tela mostra.

Com o Redis fora, tudo cai em `_do_banco`: mesma resposta, paga em SQL.

O recorte por trilha que as telas 16 e 17 pedem depende do XP por trilha, que vem
com o progresso (#30). Por ora o ranking é geral.
"""

from redis import Redis
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.cache import chave
from app.core.config import settings
from app.core.redis import executar
from app.models import Usuario
from app.schemas.ranking import EntradaRanking, Ranking

CHAVE_RANKING = chave("ranking", "xp")

# Quantos entram no pódio das telas 16 e 17.
TAMANHO_PODIO = 3


def aquecer(db: Session) -> int:
    """Reconstrói o sorted set a partir de `usuarios.xp_total`.

    Roda quando a chave não existe: primeiro request depois do deploy, depois do
    TTL vencer ou depois de o container do Redis reiniciar. Devolve quantos
    alunos entraram (0 quando não deu).
    """
    scores = {
        str(usuario_id): float(xp)
        for usuario_id, xp in db.execute(select(Usuario.id, Usuario.xp_total)).all()
    }
    if not scores:
        return 0

    def gravar(r: Redis) -> int:
        with r.pipeline() as pipe:
            # `delete` junto do `zadd` no mesmo pipeline: sem isso existe uma
            # janela em que o ranking aparece vazio para quem estiver lendo.
            pipe.delete(CHAVE_RANKING)
            pipe.zadd(CHAVE_RANKING, scores)
            pipe.expire(CHAVE_RANKING, settings.cache_ttl_ranking)
            pipe.execute()
        return len(scores)

    return executar(gravar, padrao=0) or 0


def registrar_xp(usuario_id: int, delta: int) -> None:
    """Soma `delta` ao score do aluno — a invalidação ao ganhar XP.

    Se a chave não existe, o incremento é descartado de propósito: criá-la aqui
    daria um ranking de uma linha só. O próximo `obter_ranking` reconstrói.
    """

    def incrementar(r: Redis) -> None:
        if r.exists(CHAVE_RANKING):
            r.zincrby(CHAVE_RANKING, float(delta), str(usuario_id))

    executar(incrementar)


def invalidar() -> None:
    """Descarta o ranking. Para quando o XP muda por fora: seed, correção em massa."""
    executar(lambda r: r.delete(CHAVE_RANKING))


def obter_ranking(
    db: Session,
    *,
    limite: int = 20,
    deslocamento: int = 0,
    usuario_id: int | None = None,
) -> Ranking:
    """Pódio, uma página da lista rolável e, se pedido, a posição de um aluno."""
    pagina = _fatia(db, deslocamento=deslocamento, limite=limite)
    if pagina is None:
        return _do_banco(db, limite=limite, deslocamento=deslocamento, usuario_id=usuario_id)

    podio = _fatia(db, deslocamento=0, limite=TAMANHO_PODIO) or []
    posicao_usuario = None if usuario_id is None else _posicao_de(usuario_id)

    ids = {identificador for identificador, _ in [*pagina, *podio]}
    if posicao_usuario is not None:
        ids.add(usuario_id)

    perfis = _perfis(db, ids)

    return Ranking(
        podio=_entradas(podio, perfis, inicio=0),
        lista=_entradas(pagina, perfis, inicio=deslocamento),
        total=executar(lambda r: r.zcard(CHAVE_RANKING), padrao=0) or 0,
        usuario=(
            None
            if posicao_usuario is None
            else _entrada(usuario_id, posicao_usuario[1], posicao_usuario[0], perfis)
        ),
    )


def _fatia(db: Session, *, deslocamento: int, limite: int) -> list[tuple[int, int]] | None:
    """Fatia do sorted set, do maior XP para o menor.

    `None` significa "não deu para usar o Redis" (chave ausente que não aqueceu,
    ou Redis fora) e manda quem chamou para o banco. Lista vazia é diferente:
    quer dizer que o ranking existe e está vazio.
    """
    fim = deslocamento + limite - 1

    def ler(r: Redis) -> list[tuple[int, int]] | None:
        if not r.exists(CHAVE_RANKING):
            return None
        return [
            (int(identificador), int(xp))
            for identificador, xp in r.zrevrange(CHAVE_RANKING, deslocamento, fim, withscores=True)
        ]

    fatia = executar(ler, padrao=None)
    if fatia is not None:
        return fatia

    # Chave ausente e Redis fora chegam aqui iguais: aquecer resolve o primeiro
    # caso e, no segundo, devolve 0 e a resposta sai do banco.
    return executar(ler, padrao=None) if aquecer(db) else None


def _posicao_de(usuario_id: int) -> tuple[int, int] | None:
    """Posição (começando em 1) e XP do aluno, ou None se ele não está no ranking."""

    def ler(r: Redis) -> tuple[int, int] | None:
        indice = r.zrevrank(CHAVE_RANKING, str(usuario_id))
        if indice is None:
            return None
        return indice + 1, int(r.zscore(CHAVE_RANKING, str(usuario_id)) or 0)

    return executar(ler, padrao=None)


def _perfis(db: Session, ids: set[int]) -> dict[int, Usuario]:
    if not ids:
        return {}

    consulta = select(Usuario).where(Usuario.id.in_(ids))
    return {usuario.id: usuario for usuario in db.execute(consulta).scalars()}


def _entradas(
    fatia: list[tuple[int, int]], perfis: dict[int, Usuario], *, inicio: int
) -> list[EntradaRanking]:
    entradas = (
        _entrada(identificador, xp, inicio + indice + 1, perfis)
        for indice, (identificador, xp) in enumerate(fatia)
    )
    return [entrada for entrada in entradas if entrada is not None]


def _entrada(
    usuario_id: int, xp: int, posicao: int, perfis: dict[int, Usuario]
) -> EntradaRanking | None:
    """None quando o aluno saiu do banco e o sorted set ainda não sabe disso."""
    usuario = perfis.get(usuario_id)
    return None if usuario is None else _do_modelo(usuario, posicao, xp=xp)


def _do_banco(db: Session, *, limite: int, deslocamento: int, usuario_id: int | None) -> Ranking:
    """Caminho sem Redis. `xp_total` é indexado, então é uma ordenação por índice."""
    ordenada = select(Usuario).order_by(Usuario.xp_total.desc(), Usuario.id)
    pagina = list(db.execute(ordenada.offset(deslocamento).limit(limite)).scalars())
    podio = list(db.execute(ordenada.limit(TAMANHO_PODIO)).scalars())

    return Ranking(
        podio=[_do_modelo(usuario, indice + 1) for indice, usuario in enumerate(podio)],
        lista=[
            _do_modelo(usuario, deslocamento + indice + 1) for indice, usuario in enumerate(pagina)
        ],
        total=db.execute(select(func.count(Usuario.id))).scalar_one(),
        usuario=None if usuario_id is None else _posicao_no_banco(db, usuario_id),
    )


def _posicao_no_banco(db: Session, usuario_id: int) -> EntradaRanking | None:
    posicoes = select(
        Usuario.id.label("usuario_id"),
        func.row_number().over(order_by=(Usuario.xp_total.desc(), Usuario.id)).label("posicao"),
    ).subquery()

    posicao = db.execute(
        select(posicoes.c.posicao).where(posicoes.c.usuario_id == usuario_id)
    ).scalar_one_or_none()
    if posicao is None:
        return None

    usuario = db.get(Usuario, usuario_id)
    return None if usuario is None else _do_modelo(usuario, int(posicao))


def _do_modelo(usuario: Usuario, posicao: int, *, xp: int | None = None) -> EntradaRanking:
    return EntradaRanking(
        posicao=posicao,
        usuario_id=usuario.id,
        username=usuario.username,
        nome_exibicao=usuario.nome_exibicao,
        avatar_url=usuario.avatar_url,
        xp=usuario.xp_total if xp is None else xp,
    )
