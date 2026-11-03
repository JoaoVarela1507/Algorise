"""Conversas do chat: histórico, busca, arquivamento e grupos (#33).

A troca de mensagens com o modelo continua em `services/chat.py`. Aqui fica o
que o aluno faz com o histórico. Tudo é do aluno dono: conversa ou grupo de
outro responde como inexistente (`NaoEncontrado`).

A busca procura a palavra no título e no conteúdo das mensagens. No PostgreSQL
é o full-text em português (`to_tsvector`, com índice GIN), que acha "laços"
buscando "laço"; no SQLite dos testes, um `LIKE`.
"""

from sqlalchemy import Select, exists, func, or_, select
from sqlalchemy.orm import Session

from app.models import AnexoChat, Conversa, GrupoChat, MensagemChat, Usuario
from app.schemas.conversas import EdicaoDeConversa, EdicaoDeGrupo, NovaConversa, NovoGrupo
from app.schemas.pagina import Paginacao
from app.services import anexos, chat

TITULO_PADRAO = "Nova conversa"
SUGESTOES_RECENTES = 4


class NaoEncontrado(Exception):
    """A conversa ou o grupo não existe, ou é de outro aluno."""


# --- conversas ----------------------------------------------------------------------------


def criar(db: Session, usuario: Usuario, dados: NovaConversa) -> Conversa:
    if dados.titulo:
        titulo = dados.titulo
    elif dados.primeira_mensagem and dados.primeira_mensagem.strip():
        titulo = chat.titulo_de(dados.primeira_mensagem)
    else:
        titulo = TITULO_PADRAO
    conversa = Conversa(usuario_id=usuario.id, titulo=titulo)
    db.add(conversa)
    db.commit()
    return conversa


def listar(
    db: Session,
    usuario: Usuario,
    pagina: Paginacao,
    *,
    busca: str | None = None,
    arquivadas: bool = False,
    grupo_id: int | None = None,
) -> tuple[list[Conversa], int]:
    """Uma página do histórico, da conversa mais recente para a mais antiga."""
    consulta = select(Conversa).where(
        Conversa.usuario_id == usuario.id, Conversa.arquivada.is_(arquivadas)
    )
    if grupo_id is not None:
        consulta = consulta.where(Conversa.grupo_id == grupo_id)
    if busca and busca.strip():
        consulta = _filtrar(db, consulta, busca.strip())
    total = db.scalar(select(func.count()).select_from(consulta.subquery()))
    itens = db.scalars(
        consulta.order_by(Conversa.atualizado_em.desc(), Conversa.id.desc())
        .offset(pagina.deslocamento)
        .limit(pagina.tamanho_pagina)
    ).all()
    return list(itens), total or 0


def mensagens(
    db: Session, usuario: Usuario, conversa_id: int, pagina: Paginacao
) -> tuple[list[MensagemChat], int]:
    """As mensagens da conversa, na ordem em que foram trocadas."""
    conversa = do_aluno(db, usuario, conversa_id)
    consulta = select(MensagemChat).where(MensagemChat.conversa_id == conversa.id)
    total = db.scalar(select(func.count()).select_from(consulta.subquery()))
    itens = db.scalars(
        consulta.order_by(MensagemChat.id).offset(pagina.deslocamento).limit(pagina.tamanho_pagina)
    ).all()
    return list(itens), total or 0


def editar(db: Session, usuario: Usuario, conversa_id: int, dados: EdicaoDeConversa) -> Conversa:
    conversa = do_aluno(db, usuario, conversa_id)
    campos = dados.model_dump(exclude_unset=True)
    if campos.get("grupo_id") is not None:
        _grupo_do_aluno(db, usuario, campos["grupo_id"])
    for campo, valor in campos.items():
        setattr(conversa, campo, valor)
    db.commit()
    return conversa


def apagar(db: Session, usuario: Usuario, conversa_id: int) -> None:
    """Apaga a conversa, as mensagens e os anexos (cascade), e os arquivos; o grupo continua."""
    conversa = do_aluno(db, usuario, conversa_id)
    arquivos = list(
        db.scalars(
            select(AnexoChat.arquivo)
            .join(MensagemChat)
            .where(MensagemChat.conversa_id == conversa.id)
        )
    )
    db.delete(conversa)
    db.commit()
    anexos.apagar_arquivos(arquivos)


def do_aluno(db: Session, usuario: Usuario, conversa_id: int) -> Conversa:
    conversa = db.get(Conversa, conversa_id)
    if conversa is None or conversa.usuario_id != usuario.id:
        raise NaoEncontrado
    return conversa


def sugestoes(db: Session, usuario: Usuario) -> list[dict]:
    """Tópicos para a tela 21: o passo em que o aluno está e as conversas recentes."""
    itens: list[dict] = []
    atual = chat.trilha_atual(db, usuario)
    if atual is not None:
        trilha, modulo = atual
        itens.append(
            {"texto": f"Tenho uma dúvida sobre {modulo.titulo} ({trilha.nome})", "origem": "trilha"}
        )
    recentes = db.scalars(
        select(Conversa)
        .where(Conversa.usuario_id == usuario.id, Conversa.arquivada.is_(False))
        .order_by(Conversa.atualizado_em.desc(), Conversa.id.desc())
        .limit(SUGESTOES_RECENTES)
    )
    itens.extend(
        {"texto": conversa.titulo, "origem": "conversa", "conversa_id": conversa.id}
        for conversa in recentes
        if conversa.titulo != TITULO_PADRAO
    )
    return itens


# --- grupos -------------------------------------------------------------------------------


def criar_grupo(db: Session, usuario: Usuario, dados: NovoGrupo) -> GrupoChat:
    grupo = GrupoChat(usuario_id=usuario.id, nome=dados.nome)
    db.add(grupo)
    db.flush()
    _definir_conversas(db, usuario, grupo, dados.conversa_ids)
    db.commit()
    return grupo


def listar_grupos(db: Session, usuario: Usuario) -> list[GrupoChat]:
    return list(
        db.scalars(
            select(GrupoChat).where(GrupoChat.usuario_id == usuario.id).order_by(GrupoChat.nome)
        )
    )


def obter_grupo(db: Session, usuario: Usuario, grupo_id: int) -> GrupoChat:
    return _grupo_do_aluno(db, usuario, grupo_id)


def editar_grupo(db: Session, usuario: Usuario, grupo_id: int, dados: EdicaoDeGrupo) -> GrupoChat:
    grupo = _grupo_do_aluno(db, usuario, grupo_id)
    if dados.nome is not None:
        grupo.nome = dados.nome
    if dados.conversa_ids is not None:
        _definir_conversas(db, usuario, grupo, dados.conversa_ids)
    db.commit()
    return grupo


def apagar_grupo(db: Session, usuario: Usuario, grupo_id: int) -> None:
    """Apaga o grupo; as conversas ficam, fora de grupo."""
    grupo = _grupo_do_aluno(db, usuario, grupo_id)
    grupo.conversas.clear()
    db.delete(grupo)
    db.commit()


# --- apoio --------------------------------------------------------------------------------


def _filtrar(db: Session, consulta: Select, busca: str) -> Select:
    if db.get_bind().dialect.name == "postgresql":
        tem_mensagem = exists().where(
            MensagemChat.conversa_id == Conversa.id,
            func.to_tsvector("portuguese", MensagemChat.conteudo).op("@@")(
                func.plainto_tsquery("portuguese", busca)
            ),
        )
    else:
        tem_mensagem = exists().where(
            MensagemChat.conversa_id == Conversa.id,
            MensagemChat.conteudo.ilike(f"%{busca}%"),
        )
    return consulta.where(or_(Conversa.titulo.ilike(f"%{busca}%"), tem_mensagem))


def _grupo_do_aluno(db: Session, usuario: Usuario, grupo_id: int) -> GrupoChat:
    grupo = db.get(GrupoChat, grupo_id)
    if grupo is None or grupo.usuario_id != usuario.id:
        raise NaoEncontrado
    return grupo


def _definir_conversas(db: Session, usuario: Usuario, grupo: GrupoChat, ids: list[int]) -> None:
    """O grupo passa a ter exatamente estas conversas, todas do aluno."""
    # Pela relação, e não pelo `grupo_id`, para a sessão já ver a lista nova.
    grupo.conversas = [do_aluno(db, usuario, conversa_id) for conversa_id in dict.fromkeys(ids)]
