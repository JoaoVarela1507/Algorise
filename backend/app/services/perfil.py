"""Leitura e edição do perfil do aluno, e o perfil público que os outros veem."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Curso, Instituicao, TipoTrilha, Usuario
from app.schemas.perfil import (
    AtualizacaoPerfil,
    AtualizacaoPreferencias,
    Perfil,
    PerfilPublico,
    Preferencias,
)
from app.services import niveis
from app.services import streak as servico_streak


class CursoSemInstituicao(Exception):
    """Curso informado sem instituição, nem nova nem já salva no perfil."""


def montar_perfil(db: Session, usuario: Usuario) -> Perfil:
    """Perfil para exibir. Abrir o app conta como o acesso do dia no streak."""
    streak = servico_streak.registrar_acesso(db, usuario.id)
    instituicao = db.get(Instituicao, usuario.instituicao_id) if usuario.instituicao_id else None
    curso = db.get(Curso, usuario.curso_id) if usuario.curso_id else None
    nivel, xp_no_nivel, xp_para_proximo = niveis.faixa_do_nivel(usuario.xp_total)

    return Perfil(
        id=usuario.id,
        email=usuario.email,
        username=usuario.username,
        nome_exibicao=usuario.nome_exibicao,
        avatar_url=usuario.avatar_url,
        tem_senha=usuario.tem_senha,
        xp_total=usuario.xp_total,
        nivel=nivel,
        xp_no_nivel=xp_no_nivel,
        xp_para_proximo=xp_para_proximo,
        streak_dias=streak.dias_consecutivos,
        nivel_experiencia=usuario.nivel_experiencia,
        tipo_trilha=usuario.tipo_trilha,
        instituicao=instituicao.nome if instituicao else None,
        curso=curso.nome if curso else None,
        periodo=usuario.periodo,
        preferencias=Preferencias.model_validate(usuario),
    )


def perfil_publico(db: Session, username: str) -> PerfilPublico | None:
    """Perfil reduzido de um aluno, ou None se ele não existe (ou pediu exclusão).

    Conta com exclusão agendada some como some do ranking: quem pediu para
    sair não continua exposto durante o prazo.
    """
    usuario = db.execute(
        select(Usuario).where(
            func.lower(Usuario.username) == username.lower(),
            Usuario.exclusao_agendada_para.is_(None),
        )
    ).scalar_one_or_none()
    if usuario is None:
        return None

    # `obter_streak`, e não `registrar_acesso`: ver o perfil de alguém não pode
    # contar como o acesso do dia dessa pessoa.
    streak = servico_streak.obter_streak(db, usuario.id)
    return PerfilPublico(
        username=usuario.username,
        nome_exibicao=usuario.nome_exibicao,
        avatar_url=usuario.avatar_url,
        nivel=niveis.nivel_de(usuario.xp_total),
        xp_total=usuario.xp_total,
        streak_dias=streak.dias_consecutivos,
    )


def atualizar_preferencias(
    db: Session, usuario: Usuario, dados: AtualizacaoPreferencias
) -> Preferencias:
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        # `null` não apaga: toda preferência tem um valor, nem que seja o padrão.
        if valor is not None:
            setattr(usuario, campo, valor)

    db.commit()
    db.refresh(usuario)
    return Preferencias.model_validate(usuario)


def trocar_modo_trilha(db: Session, usuario: Usuario, modo: TipoTrilha) -> Perfil:
    """Troca o modo de trilha. Não toca no progresso.

    O que fica liberado em cada modo é calculado na leitura
    (`services/progresso.py`), então não há nada para recalcular nem migrar
    aqui: o que estava concluído continua concluído.
    """
    usuario.tipo_trilha = modo
    db.commit()
    db.refresh(usuario)
    return montar_perfil(db, usuario)


def atualizar_perfil(db: Session, usuario: Usuario, dados: AtualizacaoPerfil) -> Perfil:
    campos = dados.model_dump(exclude_unset=True)

    # `null` explícito é ignorado: nenhuma dessas colunas aceita ficar vazia
    # depois de preenchida.
    for campo in ("nome_exibicao", "nivel_experiencia", "tipo_trilha", "periodo"):
        if campos.get(campo) is not None:
            setattr(usuario, campo, campos[campo])

    if campos.get("instituicao"):
        nova = _obter_ou_criar_instituicao(db, campos["instituicao"])
        if nova.id != usuario.instituicao_id:
            usuario.instituicao_id = nova.id
            # Curso é da instituição: trocar uma sem mandar o outro o invalida.
            if "curso" not in campos:
                usuario.curso_id = None

    if campos.get("curso"):
        if usuario.instituicao_id is None:
            raise CursoSemInstituicao
        usuario.curso_id = _obter_ou_criar_curso(db, usuario.instituicao_id, campos["curso"]).id

    db.commit()
    db.refresh(usuario)
    return montar_perfil(db, usuario)


def _obter_ou_criar_instituicao(db: Session, nome: str) -> Instituicao:
    nome = " ".join(nome.split())
    # Comparação sem caixa: "ufrpe" e "UFRPE" digitados por alunos diferentes
    # precisam cair no mesmo registro.
    existente = db.execute(
        select(Instituicao).where(func.lower(Instituicao.nome) == nome.lower())
    ).scalar_one_or_none()
    if existente is not None:
        return existente

    instituicao = Instituicao(nome=nome)
    db.add(instituicao)
    db.flush()
    return instituicao


def _obter_ou_criar_curso(db: Session, instituicao_id: int, nome: str) -> Curso:
    nome = " ".join(nome.split())
    existente = db.execute(
        select(Curso).where(
            Curso.instituicao_id == instituicao_id, func.lower(Curso.nome) == nome.lower()
        )
    ).scalar_one_or_none()
    if existente is not None:
        return existente

    curso = Curso(instituicao_id=instituicao_id, nome=nome)
    db.add(curso)
    db.flush()
    return curso
