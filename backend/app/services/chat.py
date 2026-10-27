"""Regras do chat com IA (#11): contexto do aluno, histórico e gravação.

O prompt é da skill do tutor (`app/ia/skills/tutor.py`); aqui fica o que depende
do banco. O fluxo de uma mensagem tem três tempos, e a rota é quem os encadeia:

1. `preparar`: confere a conversa e monta o que vai para o modelo. Não grava
   nada, para a IA fora do ar não deixar uma pergunta sem resposta no histórico;
2. `registrar_pergunta`: grava a pergunta, depois que o modelo começou a
   responder;
3. `registrar_resposta`: grava a resposta, inteira ou o que deu tempo de gerar.
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.ia import MensagemIA
from app.ia.skills import tutor
from app.models import (
    Conversa,
    Curso,
    Instituicao,
    MensagemChat,
    ModoResposta,
    Modulo,
    PapelMensagem,
    ProgressoUsuario,
    StatusProgresso,
    Trilha,
    Usuario,
)

TAMANHO_DO_TITULO = 80


class ConversaNaoEncontrada(Exception):
    """A conversa não existe ou é de outro aluno."""


@dataclass(frozen=True)
class Preparo:
    conversa_id: int | None
    contexto: list[MensagemIA]
    max_tokens: int


def preparar(
    db: Session, usuario: Usuario, conversa_id: int | None, conteudo: str, modo: ModoResposta
) -> Preparo:
    """Monta o pedido ao modelo: instrução, histórico da conversa e a pergunta."""
    historico: list[MensagemChat] = []
    if conversa_id is not None:
        conversa = db.get(Conversa, conversa_id)
        if conversa is None or conversa.usuario_id != usuario.id:
            raise ConversaNaoEncontrada
        historico = _ultimas_mensagens(db, conversa_id)

    contexto = tutor.mensagens(
        aluno_do_tutor(db, usuario),
        modo,
        [
            MensagemIA("user" if m.papel is PapelMensagem.usuario else "assistant", m.conteudo)
            for m in historico
        ],
        conteudo,
    )
    return Preparo(conversa_id, contexto, tutor.max_tokens(modo))


def aluno_do_tutor(db: Session, usuario: Usuario) -> tutor.Aluno:
    """O que o perfil e o progresso dizem do aluno, no formato da skill."""
    curso = db.get(Curso, usuario.curso_id) if usuario.curso_id else None
    instituicao = db.get(Instituicao, usuario.instituicao_id) if usuario.instituicao_id else None
    atual = trilha_atual(db, usuario)
    return tutor.Aluno(
        nivel=usuario.nivel_experiencia,
        curso=curso.nome if curso else None,
        instituicao=instituicao.nome if instituicao else None,
        periodo=usuario.periodo,
        trilha=atual[0].nome if atual else None,
        disciplina=atual[0].disciplina if atual else None,
        modulo=atual[1].titulo if atual else None,
    )


def trilha_atual(db: Session, usuario: Usuario) -> tuple[Trilha, Modulo] | None:
    """O módulo em andamento mexido por último, com a trilha dele."""
    linha = db.execute(
        select(Trilha, Modulo)
        .join(ProgressoUsuario, ProgressoUsuario.modulo_id == Modulo.id)
        .join(Trilha, Trilha.id == ProgressoUsuario.trilha_id)
        .where(
            ProgressoUsuario.usuario_id == usuario.id,
            ProgressoUsuario.status == StatusProgresso.em_andamento,
        )
        .order_by(ProgressoUsuario.atualizado_em.desc(), ProgressoUsuario.id.desc())
        .limit(1)
    ).first()
    return (linha[0], linha[1]) if linha else None


def registrar_pergunta(
    db: Session, usuario: Usuario, conversa_id: int | None, conteudo: str
) -> tuple[Conversa, MensagemChat]:
    """Grava a pergunta, abrindo a conversa se for a primeira mensagem."""
    if conversa_id is None:
        conversa = Conversa(usuario_id=usuario.id, titulo=titulo_de(conteudo))
        db.add(conversa)
    else:
        conversa = db.get_one(Conversa, conversa_id)
        conversa.atualizado_em = func.now()

    mensagem = MensagemChat(conversa=conversa, papel=PapelMensagem.usuario, conteudo=conteudo)
    db.add(mensagem)
    db.commit()
    db.refresh(conversa)
    return conversa, mensagem


def registrar_resposta(
    fabrica: sessionmaker[Session], conversa_id: int, conteudo: str, *, incompleta: bool
) -> int | None:
    """Grava a resposta do assistente. Sem texto nenhum, não há o que gravar.

    Abre a própria sessão: roda no fim do streaming, quando a do request pode já
    ter fechado.
    """
    if not conteudo:
        return None
    with fabrica() as db:
        mensagem = MensagemChat(
            conversa_id=conversa_id,
            papel=PapelMensagem.assistente,
            conteudo=conteudo,
            incompleta=incompleta,
        )
        db.add(mensagem)
        conversa = db.get_one(Conversa, conversa_id)
        conversa.atualizado_em = func.now()
        db.commit()
        return mensagem.id


def titulo_de(conteudo: str) -> str:
    """Primeira linha da pergunta, cortada num tamanho que cabe na lista."""
    linha = " ".join(conteudo.strip().splitlines()[0].split()) if conteudo.strip() else ""
    if len(linha) <= TAMANHO_DO_TITULO:
        return linha or "Nova conversa"
    return linha[: TAMANHO_DO_TITULO - 1].rstrip() + "…"


def _ultimas_mensagens(db: Session, conversa_id: int) -> list[MensagemChat]:
    """As mensagens mais recentes da conversa, da mais antiga para a mais nova."""
    recentes = db.scalars(
        select(MensagemChat)
        .where(MensagemChat.conversa_id == conversa_id)
        .order_by(MensagemChat.id.desc())
        .limit(settings.chat_janela_historico)
    ).all()
    return list(reversed(recentes))
