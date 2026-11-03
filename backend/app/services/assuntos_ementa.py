"""Da ementa aos assuntos, e dos assuntos ao catálogo (#38).

Roda depois da extração do texto (`services/ementas.py`), em duas etapas:

1. **Leitura**: a skill `ler_ementa` transforma o texto em disciplinas e
   assuntos. Uma ementa com o mesmo PDF que outra já lida copia as disciplinas
   dela, sem chamar a IA.
2. **Mapeamento**: cada assunto é buscado no vault entre o que aponta para um
   módulo (o texto do módulo e a transcrição do vídeo). Perto o bastante
   (`ementa_distancia_maxima`), o assunto está coberto por aquele módulo; senão,
   vira uma lacuna, a mesma para todas as ementas que pedem o assunto.

O mapeamento roda sempre, mesmo na cópia: o catálogo pode ter crescido desde a
primeira leitura, e uma lacuna de ontem pode estar coberta hoje.

**Em duas levas.** Na CPU, cada parte do texto leva minutos no modelo. As partes
com cara de programação (`ler_ementa.priorizar`) são lidas primeiro: com elas,
os assuntos ficam prontos e o aluno já revisa e começa a trilha guiada. O resto
é lido em seguida, na mesma tarefa, e as disciplinas e os assuntos novos são
acrescentados (`partes_pendentes` conta o que falta). Uma parte que o modelo
devolve inválida é pulada; a leitura só falha se nenhuma parte da leva der certo.

Só as disciplinas de programação (a IA marca, o aluno corrige) entram na
trilha guiada e vão ao catálogo; as demais ficam guardadas, sem ligação.

Depois da leitura, o aluno revisa (`revisar`): corrige, remove e acrescenta
assuntos, e escolhe as disciplinas da trilha. Só o que ele mudou é buscado de
novo no vault. E confirma (`confirmar`), o que faz da ementa a base da trilha
guiada dele.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.fila import fila_das_tarefas
from app.ia import IAIndisponivel, ProvedorIA
from app.ia.skills import ler_ementa
from app.ia.vault import buscar_por_vetor, registrar_modulos
from app.ia.vault.ingestao import LOTE_DE_EMBEDDING
from app.models import (
    AssuntoEmenta,
    DisciplinaEmenta,
    Ementa,
    Lacuna,
    Modulo,
    StatusAssuntos,
    StatusLacuna,
)

logger = logging.getLogger(__name__)

ERRO_IA_FORA = "A leitura dos assuntos está indisponível agora. Tente de novo em alguns minutos."
ERRO_SEM_DISCIPLINAS = "Não encontramos disciplinas com conteúdo programático no texto da ementa."
ERRO_SAIDA_INVALIDA = "Não conseguimos identificar as disciplinas da ementa. Tente de novo."


async def processar(db: Session, provedor: ProvedorIA, ementa: Ementa) -> None:
    """Lê e mapeia os assuntos da ementa. Nunca levanta: a falha vira `falhou`, com o motivo."""
    ementa.status_assuntos = StatusAssuntos.processando
    ementa.erro_assuntos = None
    ementa.partes_pendentes = 0
    db.commit()

    resto: list[str] = []
    try:
        # Um módulo criado ou editado desde a última ementa só é achado se
        # estiver no vault. Sem mudança, isto não pede embedding nenhum. Vem
        # primeiro porque grava (e confirma) por conta própria: o que vem
        # depois fica numa transação só, desfeita inteira se algo falhar.
        await registrar_modulos(db, provedor)
        disciplinas = _copiar_de_outra(db, ementa)
        if not disciplinas:
            primeiras, resto = ler_ementa.priorizar(_partes(ementa))
            leituras = await _ler(provedor, primeiras)
            if resto and not any(d.programacao and d.assuntos for d in ler_ementa.juntar(leituras)):
                # Nada para a trilha na primeira leva: não adianta liberar a
                # revisão sem ela. Lê o resto agora mesmo.
                leituras += await _ler(provedor, resto)
                resto = []
            disciplinas = ler_ementa.juntar(leituras)
        if not any(d.assuntos for d in disciplinas):
            raise _Falha(ERRO_SEM_DISCIPLINAS)
        # Releitura: apaga as disciplinas antigas antes de inserir as novas,
        # que reusam as mesmas `ordem` (únicas por ementa).
        ementa.disciplinas.clear()
        db.flush()
        ementa.disciplinas = _montar(disciplinas)
        await mapear(db, provedor, _da_trilha(ementa))
    except _Falha as erro:
        db.rollback()
        _falhar(db, ementa, str(erro))
        return
    except IAIndisponivel:
        logger.warning("IA indisponível ao ler os assuntos da ementa %s", ementa.id, exc_info=True)
        db.rollback()
        _falhar(db, ementa, ERRO_IA_FORA)
        return
    except ler_ementa.SaidaInvalida:
        logger.warning("Saída inválida da IA na ementa %s", ementa.id, exc_info=True)
        db.rollback()
        _falhar(db, ementa, ERRO_SAIDA_INVALIDA)
        return

    ementa.status_assuntos = StatusAssuntos.prontos
    ementa.partes_pendentes = len(resto)
    db.commit()
    disparar_busca(ementa)
    if resto:
        await _completar(db, provedor, ementa, resto)


async def _completar(db: Session, provedor: ProvedorIA, ementa: Ementa, partes: list[str]) -> None:
    """A segunda leva: acrescenta o que as partes restantes trazem.

    Disciplina nova entra no fim; a que já existe ganha os assuntos que ela
    ainda não tinha. Os de programação vão ao catálogo, e a busca de conteúdo
    roda de novo. Uma falha aqui não desfaz a primeira leva: só para de ler.
    """
    try:
        lidas = ler_ementa.juntar(await _ler(provedor, partes))
        novos = _acrescentar(ementa, lidas)
        db.flush()
        if novos:
            await mapear(db, provedor, novos)
    except (IAIndisponivel, ler_ementa.SaidaInvalida):
        logger.warning(
            "A segunda leva da ementa %s não foi lida; fica a primeira", ementa.id, exc_info=True
        )
        db.rollback()
        novos = []
    ementa.partes_pendentes = 0
    db.commit()
    if novos:
        disparar_busca(ementa)


def _acrescentar(ementa: Ementa, lidas: list[ler_ementa.Disciplina]) -> list[AssuntoEmenta]:
    """Junta as disciplinas lidas às da ementa. Devolve os assuntos novos da trilha."""
    existentes = {ler_ementa.normalizar(d.nome): d for d in ementa.disciplinas}
    proxima = max((d.ordem for d in ementa.disciplinas), default=-1) + 1
    novos: list[AssuntoEmenta] = []
    for lida in lidas:
        if not lida.assuntos:
            continue
        atual = existentes.get(ler_ementa.normalizar(lida.nome))
        if atual is None:
            [atual] = _montar([lida])
            atual.ordem = proxima
            proxima += 1
            ementa.disciplinas.append(atual)
            existentes[ler_ementa.normalizar(lida.nome)] = atual
            acrescentados = list(atual.assuntos)
        else:
            vistos = {ler_ementa.normalizar(a.texto) for a in atual.assuntos}
            ordem = max((a.ordem for a in atual.assuntos), default=-1) + 1
            acrescentados = []
            for texto in lida.assuntos:
                if ler_ementa.normalizar(texto) in vistos:
                    continue
                vistos.add(ler_ementa.normalizar(texto))
                assunto = AssuntoEmenta(ordem=ordem, texto=texto)
                ordem += 1
                atual.assuntos.append(assunto)
                acrescentados.append(assunto)
        if atual.na_trilha:
            novos += acrescentados
    return novos


async def revisar(
    db: Session, provedor: ProvedorIA, ementa: Ementa, disciplinas: list[ler_ementa.Disciplina]
) -> None:
    """Troca as disciplinas e os assuntos da ementa pelos que o aluno revisou.

    O assunto que já existia (mesma disciplina e mesmo texto, sem contar acento
    e caixa) mantém a ligação que tinha; só o novo, o renomeado e o de uma
    disciplina que acabou de entrar na trilha vão ao vault. Em `disciplinas`,
    `programacao` é o que o aluno marcou para a trilha. Levanta `IAIndisponivel`
    sem mudar nada, se o vault precisar da IA e ela estiver fora.
    """
    disciplinas = ler_ementa.juntar([ler_ementa.Leitura(disciplinas=disciplinas)])
    # Só o assunto que estava na trilha tem ligação: o de fora nunca foi ao vault.
    ligacoes = {
        _chave(a.disciplina.nome, a.texto): (a.modulo, a.lacuna, a.distancia)
        for a in _da_trilha(ementa)
        if a.modulo is not None or a.lacuna is not None
    }
    tem_novo = any(
        _chave(d.nome, a) not in ligacoes for d in disciplinas if d.programacao for a in d.assuntos
    )
    try:
        if tem_novo:
            # Antes de mexer na ementa: o registro confirma a transação por
            # conta própria (ver `processar`).
            await registrar_modulos(db, provedor)
        ementa.disciplinas.clear()
        db.flush()
        ementa.disciplinas = _montar(disciplinas)
        novos = []
        for assunto in _da_trilha(ementa):
            ligacao = ligacoes.get(_chave(assunto.disciplina.nome, assunto.texto))
            if ligacao is None:
                novos.append(assunto)
            else:
                assunto.modulo, assunto.lacuna, assunto.distancia = ligacao
        await mapear(db, provedor, novos)
    except Exception:
        db.rollback()
        raise
    db.commit()
    disparar_busca(ementa)


def disparar_busca(ementa: Ementa) -> None:
    """Põe na fila a busca de vídeos (#207) das disciplinas com lacuna pendente.

    A busca é uma por disciplina, e a fila não deixa duas da mesma ao mesmo
    tempo. Uma falha aqui (o Redis fora) não desfaz a leitura: as lacunas
    continuam `pendente`, e a próxima ementa da disciplina tenta de novo.
    """
    disciplinas = {
        a.lacuna.disciplina
        for a in _da_trilha(ementa)
        if a.lacuna is not None and a.lacuna.status is StatusLacuna.pendente
    }
    for disciplina in sorted(disciplinas):
        try:
            fila_das_tarefas().busca_de_conteudo(disciplina)
        except Exception:
            logger.exception("Não deu para enfileirar a busca de %s", disciplina)


def confirmar(db: Session, ementa: Ementa) -> bool:
    """Faz da ementa a base da trilha guiada. `False` se os assuntos não estão prontos."""
    if ementa.status_assuntos is not StatusAssuntos.prontos:
        return False
    # Confirmar de novo atualiza a data: a confirmada por último é a que vale.
    ementa.confirmada_em = datetime.now(UTC)
    db.commit()
    return True


async def mapear(db: Session, provedor: ProvedorIA, assuntos: list[AssuntoEmenta]) -> None:
    """Liga cada assunto ao módulo que o cobre ou a uma lacuna.

    Usa o vault como está: quem chama garante que os módulos estão nele
    (`registrar_modulos`).
    """
    textos = [f"{a.disciplina.nome}: {a.texto}" for a in assuntos]
    vetores: list[list[float]] = []
    for inicio in range(0, len(textos), LOTE_DE_EMBEDDING):
        vetores.extend(await provedor.embeddings(textos[inicio : inicio + LOTE_DE_EMBEDDING]))

    for assunto, vetor in zip(assuntos, vetores, strict=True):
        [mais_perto, *_] = buscar_por_vetor(db, vetor, com_modulo=True, limite=1) or [None]
        assunto.distancia = mais_perto.distancia if mais_perto else None
        if mais_perto is not None and mais_perto.distancia <= settings.ementa_distancia_maxima:
            # A relação, e não só o id: quem responde na mesma sessão (a
            # revisão) lê `assunto.modulo` logo em seguida.
            assunto.modulo = db.get(Modulo, mais_perto.modulo_id)
            assunto.lacuna = None
        else:
            assunto.modulo = None
            assunto.lacuna = _lacuna(db, assunto.disciplina.nome, assunto.texto)


def _partes(ementa: Ementa) -> list[str]:
    return ler_ementa.dividir_texto(ler_ementa.sem_bibliografia(ementa.texto_extraido or ""))


async def _ler(provedor: ProvedorIA, partes: list[str]) -> list[ler_ementa.Leitura]:
    """Uma leitura por parte. A parte com resposta inválida é pulada.

    Levanta `SaidaInvalida` só se todas forem inválidas: uma resposta quebrada
    (o modelo que se repete até o teto de tokens) não derruba as outras.
    """
    leituras: list[ler_ementa.Leitura] = []
    for indice, parte in enumerate(partes):
        pedacos = [
            pedaco
            async for pedaco in provedor.gerar(
                ler_ementa.mensagens(parte),
                max_tokens=ler_ementa.MAXIMO_DE_TOKENS,
                formato=ler_ementa.FORMATO,
            )
        ]
        try:
            leituras.append(ler_ementa.ler_resposta("".join(pedacos)))
        except ler_ementa.SaidaInvalida:
            logger.warning("Parte %s de %s com resposta inválida, pulada", indice + 1, len(partes))
    if partes and not leituras:
        raise ler_ementa.SaidaInvalida("Nenhuma parte devolveu uma leitura válida")
    return leituras


def _copiar_de_outra(db: Session, ementa: Ementa) -> list[ler_ementa.Disciplina]:
    """As disciplinas de outra ementa com o mesmo PDF, já lida. Vazio se não houver."""
    if ementa.hash_sha256 is None:
        return []
    outra = db.scalars(
        select(Ementa)
        .where(
            Ementa.hash_sha256 == ementa.hash_sha256,
            Ementa.id != ementa.id,
            Ementa.status_assuntos == StatusAssuntos.prontos,
        )
        .limit(1)
    ).first()
    if outra is None:
        return []
    return [
        ler_ementa.Disciplina(
            nome=d.nome,
            periodo=d.periodo,
            carga_horaria=d.carga_horaria,
            programacao=d.na_trilha,
            assuntos=[a.texto for a in d.assuntos],
        )
        for d in outra.disciplinas
    ]


def _montar(disciplinas: list[ler_ementa.Disciplina]) -> list[DisciplinaEmenta]:
    return [
        DisciplinaEmenta(
            ordem=i,
            nome=d.nome,
            periodo=d.periodo,
            carga_horaria=d.carga_horaria,
            na_trilha=d.programacao,
            assuntos=[AssuntoEmenta(ordem=j, texto=texto) for j, texto in enumerate(d.assuntos)],
        )
        for i, d in enumerate(disciplinas)
        if d.assuntos
    ]


def _da_trilha(ementa: Ementa) -> list[AssuntoEmenta]:
    """Os assuntos das disciplinas que entram na trilha guiada.

    Só eles vão ao catálogo: um assunto de Cálculo virando lacuna faria a busca
    de conteúdo (#207) procurar Cálculo no YouTube.
    """
    return [a for d in ementa.disciplinas if d.na_trilha for a in d.assuntos]


def _chave(disciplina: str, assunto: str) -> str:
    return f"{ler_ementa.normalizar(disciplina)}|{ler_ementa.normalizar(assunto)}"


def _lacuna(db: Session, disciplina: str, assunto: str) -> Lacuna:
    """A lacuna do assunto, criada na primeira ementa que o pede."""
    chave = _chave(disciplina, assunto)
    lacuna = db.scalar(select(Lacuna).where(Lacuna.chave == chave))
    if lacuna is not None:
        return lacuna
    try:
        # Outra ementa lida ao mesmo tempo pode criar a mesma lacuna: o
        # savepoint deixa perder a corrida sem desfazer o resto da leitura.
        with db.begin_nested():
            lacuna = Lacuna(chave=chave, disciplina=disciplina, assunto=assunto)
            db.add(lacuna)
        return lacuna
    except IntegrityError:
        return db.scalars(select(Lacuna).where(Lacuna.chave == chave)).one()


def _falhar(db: Session, ementa: Ementa, motivo: str) -> None:
    ementa.status_assuntos = StatusAssuntos.falhou
    ementa.erro_assuntos = motivo
    db.commit()


class _Falha(Exception):
    """Falha esperada, com a mensagem para o aluno."""
