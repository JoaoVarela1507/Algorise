"""A trilha guiada do aluno, montada da ementa que ele confirmou (#38)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import UsuarioAtual
from app.core.database import get_db
from app.core.erros import ErroDeNegocio
from app.models import StatusProgresso, Trilha
from app.schemas.trilha_guiada import ItemGuiado, ModuloGuiado, TrilhaGuiada
from app.services import progresso
from app.services import trilha_guiada as servico

router = APIRouter(prefix="/trilha-guiada", tags=["trilhas"])


@router.get(
    "",
    response_model=TrilhaGuiada,
    summary="Trilha guiada do aluno",
    description=(
        "Os assuntos da ementa confirmada por último, em ordem de estudo: módulos do "
        "catálogo, com o estado do passo, e lacunas ainda sem conteúdo. 404 se o aluno "
        "ainda não confirmou uma ementa (`POST /ementas/{id}/confirmar`)."
    ),
)
def obter_trilha_guiada(usuario: UsuarioAtual, db: Session = Depends(get_db)) -> TrilhaGuiada:
    ementa, itens = servico.montar(db, usuario)
    if ementa is None or ementa.confirmada_em is None:
        raise ErroDeNegocio(
            status_code=status.HTTP_404_NOT_FOUND,
            code="trilha_guiada_inexistente",
            message="Confirme os assuntos da sua ementa para gerar a trilha guiada",
        )

    # O estado vem da mesma regra das trilhas do catálogo, uma vez por trilha:
    # a tela e a API não podem discordar sobre o que está aberto.
    trilhas: dict[int, Trilha] = {i.modulo.trilha.id: i.modulo.trilha for i in itens if i.modulo}
    estados: dict[int, StatusProgresso] = {}
    for trilha in trilhas.values():
        estados |= progresso.estados_dos_passos(db, usuario=usuario, trilha=trilha)

    saida = [
        ItemGuiado(
            tipo="modulo" if item.modulo else "lacuna",
            disciplina=item.disciplina,
            periodo=item.periodo,
            assuntos=item.assuntos,
            base=item.base,
            modulo=ModuloGuiado(
                id=item.modulo.id,
                titulo=item.modulo.titulo,
                ordem=item.modulo.ordem,
                trilha_slug=item.modulo.trilha.slug,
                trilha_nome=item.modulo.trilha.nome,
                status=estados[item.modulo.id],
            )
            if item.modulo
            else None,
            status_lacuna=item.lacuna.status if item.lacuna else None,
        )
        for item in itens
    ]
    modulos = [i.modulo for i in saida if i.modulo]
    return TrilhaGuiada(
        ementa_id=ementa.id,
        confirmada_em=ementa.confirmada_em,
        nivel=usuario.nivel_experiencia,
        itens=saida,
        total_modulos=len(modulos),
        concluidos=sum(1 for m in modulos if m.status is StatusProgresso.concluido),
    )
