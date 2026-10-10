"""Ranking de XP servido de sorted sets do Redis.

Cada sorted set guarda `usuario_id -> xp`: pódio, página da lista rolável e
posição do aluno saem dele em O(log n), sem ordenar a tabela de usuários a cada
abertura de tela. Quem grava XP mantém o score em dia (`app/services/xp.py`),
então a invalidação é explícita e o TTL é só a rede de segurança.

São dois recortes, e as telas 16 e 17 usam os dois:

- **geral**, somando todo o XP do aluno — vem de `usuarios.xp_total`;
- **por trilha**, somando só o XP ganho nela — vem de `xp_eventos.trilha_id`.

O XP por trilha sai dos eventos, e não de um saldo desnormalizado, porque não
existe "saldo por trilha" em lugar nenhum: `xp_eventos` é a fonte da verdade, e
somar por `GROUP BY` ali é exato por construção.

Nome e avatar continuam vindo do banco: mudam sem passar por XP, e a consulta é
um `id IN (...)` dos poucos alunos que a tela mostra.

Com o Redis fora, tudo cai em `_do_banco`: mesma resposta, paga em SQL.

Conta com exclusão agendada (#40) não aparece: sai dos sorted sets no pedido e é
filtrada nas consultas ao banco.
"""

from redis import Redis
from sqlalchemy import Result, func, select
from sqlalchemy.orm import Session

from app.core.cache import chave
from app.core.config import settings
from app.core.redis import executar
from app.models import Usuario, XPEvento
from app.schemas.ranking import EntradaRanking, Ranking

PREFIXO_RANKING = chave("ranking")
CHAVE_RANKING = f"{PREFIXO_RANKING}:xp"

# Só contas ativas entram no ranking.
_ATIVAS = Usuario.exclusao_agendada_para.is_(None)

# Quantos entram no pódio das telas 16 e 17.
TAMANHO_PODIO = 3


def chave_do_ranking(trilha_id: int | None = None) -> str:
    """Sorted set do recorte pedido: o geral, ou o de uma trilha."""
    return CHAVE_RANKING if trilha_id is None else f"{PREFIXO_RANKING}:trilha:{trilha_id}"


def aquecer(db: Session, trilha_id: int | None = None) -> int:
    """Reconstrói o sorted set a partir do banco.

    Roda quando a chave não existe: primeiro request depois do deploy, depois do
    TTL vencer ou depois de o container do Redis reiniciar. Devolve quantos
    alunos entraram (0 quando não deu).
    """
    scores = {str(usuario_id): float(xp) for usuario_id, xp in _xp_do_banco(db, trilha_id).all()}
    if not scores:
        return 0

    nome = chave_do_ranking(trilha_id)

    def gravar(r: Redis) -> int:
        with r.pipeline() as pipe:
            # `delete` junto do `zadd` no mesmo pipeline: sem isso existe uma
            # janela em que o ranking aparece vazio para quem estiver lendo.
            pipe.delete(nome)
            pipe.zadd(nome, scores)
            pipe.expire(nome, settings.cache_ttl_ranking)
            pipe.execute()
        return len(scores)

    return executar(gravar, padrao=0) or 0


def registrar_xp(usuario_id: int, delta: int, trilha_id: int | None = None) -> None:
    """Soma `delta` aos scores do aluno — a invalidação ao ganhar XP.

    Atualiza o ranking geral e, quando o XP veio de uma trilha, o dela.

    Chave que não existe é ignorada de propósito: criá-la aqui daria um ranking
    de uma linha só. O próximo `obter_ranking` reconstrói do banco.
    """
    nomes = [CHAVE_RANKING]
    if trilha_id is not None:
        nomes.append(chave_do_ranking(trilha_id))

    def incrementar(r: Redis) -> None:
        for nome in nomes:
            if r.exists(nome):
                r.zincrby(nome, float(delta), str(usuario_id))

    executar(incrementar)


def remover(usuario_id: int) -> None:
    """Tira o aluno de todos os rankings: exclusão agendada ou expurgada."""

    def apagar(r: Redis) -> None:
        r.zrem(CHAVE_RANKING, str(usuario_id))
        for nome in r.scan_iter(match=f"{PREFIXO_RANKING}:trilha:*", count=100):
            r.zrem(nome, str(usuario_id))

    executar(apagar)


def invalidar(trilha_id: int | None = None) -> None:
    """Descarta um ranking. Para quando o XP muda por fora: seed, correção em massa."""
    executar(lambda r: r.delete(chave_do_ranking(trilha_id)))


def obter_ranking(
    db: Session,
    *,
    trilha_id: int | None = None,
    limite: int = 20,
    deslocamento: int = 0,
    usuario_id: int | None = None,
) -> Ranking:
    """Pódio, uma página da lista rolável e, se pedido, a posição de um aluno."""
    pagina = _fatia(db, trilha_id=trilha_id, deslocamento=deslocamento, limite=limite)
    if pagina is None:
        return _do_banco(
            db,
            trilha_id=trilha_id,
            limite=limite,
            deslocamento=deslocamento,
            usuario_id=usuario_id,
        )

    podio = _fatia(db, trilha_id=trilha_id, deslocamento=0, limite=TAMANHO_PODIO) or []
    posicao_usuario = None if usuario_id is None else _posicao_de(usuario_id, trilha_id=trilha_id)

    ids = {identificador for identificador, _ in [*pagina, *podio]}
    if posicao_usuario is not None:
        ids.add(usuario_id)

    perfis = _perfis(db, ids)
    nome = chave_do_ranking(trilha_id)

    return Ranking(
        podio=_entradas(podio, perfis, inicio=0),
        lista=_entradas(pagina, perfis, inicio=deslocamento),
        total=executar(lambda r: r.zcard(nome), padrao=0) or 0,
        usuario=(
            None
            if posicao_usuario is None
            else _entrada(usuario_id, posicao_usuario[1], posicao_usuario[0], perfis)
        ),
    )


def _xp_do_banco(db: Session, trilha_id: int | None) -> Result[tuple[int, int]]:
    """`(usuario_id, xp)` de todos os alunos ativos, no recorte pedido."""
    if trilha_id is None:
        return db.execute(select(Usuario.id, Usuario.xp_total).where(_ATIVAS))

    return db.execute(
        select(XPEvento.usuario_id, func.sum(XPEvento.valor))
        .join(Usuario, Usuario.id == XPEvento.usuario_id)
        .where(XPEvento.trilha_id == trilha_id, _ATIVAS)
        .group_by(XPEvento.usuario_id)
    )


def _fatia(
    db: Session, *, trilha_id: int | None, deslocamento: int, limite: int
) -> list[tuple[int, int]] | None:
    """Fatia do sorted set, do maior XP para o menor.

    `None` significa "não deu para usar o Redis" (chave ausente que não aqueceu,
    ou Redis fora) e manda quem chamou para o banco. Lista vazia é diferente:
    quer dizer que o ranking existe e está vazio.
    """
    fim = deslocamento + limite - 1
    nome = chave_do_ranking(trilha_id)

    def ler(r: Redis) -> list[tuple[int, int]] | None:
        if not r.exists(nome):
            return None
        return [
            (int(identificador), int(xp))
            for identificador, xp in r.zrevrange(nome, deslocamento, fim, withscores=True)
        ]

    fatia = executar(ler, padrao=None)
    if fatia is not None:
        return fatia

    # Chave ausente e Redis fora chegam aqui iguais: aquecer resolve o primeiro
    # caso e, no segundo, devolve 0 e a resposta sai do banco.
    return executar(ler, padrao=None) if aquecer(db, trilha_id) else None


def _posicao_de(usuario_id: int, *, trilha_id: int | None) -> tuple[int, int] | None:
    """Posição (começando em 1) e XP do aluno, ou None se ele não está no ranking."""
    nome = chave_do_ranking(trilha_id)

    def ler(r: Redis) -> tuple[int, int] | None:
        indice = r.zrevrank(nome, str(usuario_id))
        if indice is None:
            return None
        return indice + 1, int(r.zscore(nome, str(usuario_id)) or 0)

    return executar(ler, padrao=None)


def _perfis(db: Session, ids: set[int]) -> dict[int, Usuario]:
    if not ids:
        return {}

    # `_ATIVAS` também aqui: o sorted set pode ter ficado com o aluno se o Redis
    # estava fora na hora do pedido de exclusão.
    consulta = select(Usuario).where(Usuario.id.in_(ids), _ATIVAS)
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


def _do_banco(
    db: Session,
    *,
    trilha_id: int | None,
    limite: int,
    deslocamento: int,
    usuario_id: int | None,
) -> Ranking:
    """Caminho sem Redis: mesma resposta, paga em SQL."""
    # Uma consulta só, ordenada: a página e o pódio saem dela, e o total é o
    # tamanho. Para o ranking geral isso é uma ordenação por índice
    # (`xp_total`); para o da trilha, um `GROUP BY` sobre `xp_eventos`.
    linhas = _xp_do_banco(db, trilha_id).all()
    ordenadas = sorted(linhas, key=lambda linha: (-int(linha[1] or 0), linha[0]))

    perfis = _perfis(db, {identificador for identificador, _ in ordenadas})
    posicoes = [
        (identificador, int(xp or 0), indice + 1)
        for indice, (identificador, xp) in enumerate(ordenadas)
    ]

    def montar(fatia: list[tuple[int, int, int]]) -> list[EntradaRanking]:
        entradas = (_entrada(ident, xp, posicao, perfis) for ident, xp, posicao in fatia)
        return [entrada for entrada in entradas if entrada is not None]

    do_aluno = next((linha for linha in posicoes if linha[0] == usuario_id), None)

    return Ranking(
        podio=montar(posicoes[:TAMANHO_PODIO]),
        lista=montar(posicoes[deslocamento : deslocamento + limite]),
        total=len(posicoes),
        usuario=(
            None if do_aluno is None else _entrada(do_aluno[0], do_aluno[1], do_aluno[2], perfis)
        ),
    )


def _do_modelo(usuario: Usuario, posicao: int, *, xp: int | None = None) -> EntradaRanking:
    return EntradaRanking(
        posicao=posicao,
        usuario_id=usuario.id,
        username=usuario.username,
        nome_exibicao=usuario.nome_exibicao,
        avatar_url=usuario.avatar_url,
        xp=usuario.xp_total if xp is None else xp,
    )
