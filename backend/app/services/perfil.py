"""Leitura e edição do perfil do aluno."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Curso, Instituicao, Usuario
from app.schemas.perfil import AtualizacaoPerfil, Perfil
from app.services import streak as servico_streak


class CursoSemInstituicao(Exception):
    """Curso informado sem instituição, nem nova nem já salva no perfil."""


def montar_perfil(db: Session, usuario: Usuario) -> Perfil:
    """Perfil para exibir. Abrir o app conta como o acesso do dia no streak."""
    streak = servico_streak.registrar_acesso(db, usuario.id)
    instituicao = db.get(Instituicao, usuario.instituicao_id) if usuario.instituicao_id else None
    curso = db.get(Curso, usuario.curso_id) if usuario.curso_id else None

    return Perfil(
        id=usuario.id,
        email=usuario.email,
        username=usuario.username,
        nome_exibicao=usuario.nome_exibicao,
        avatar_url=usuario.avatar_url,
        tem_senha=usuario.tem_senha,
        xp_total=usuario.xp_total,
        streak_dias=streak.dias_consecutivos,
        nivel_experiencia=usuario.nivel_experiencia,
        tipo_trilha=usuario.tipo_trilha,
        instituicao=instituicao.nome if instituicao else None,
        curso=curso.nome if curso else None,
        periodo=usuario.periodo,
    )


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
