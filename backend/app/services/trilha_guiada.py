"""Trilha guiada do aluno: os assuntos da ementa confirmada, em ordem de estudo (#38).

Não há tabela da trilha guiada. Ela é calculada a cada leitura a partir da
ementa que o aluno confirmou por último (`Ementa.confirmada_em`): quando uma
lacuna for coberta (#210), ou o aluno corrigir um assunto, a trilha muda sem
nada para sincronizar.

Entram só as disciplinas de programação (`na_trilha`). A ordem é a do curso: as
disciplinas pelo período e, dentro dele, pela ordem do
documento; os assuntos, na ordem do conteúdo programático. Cada item é um
módulo do catálogo, que pode cobrir mais de um assunto e aparece uma vez só, ou
uma lacuna, que ainda espera conteúdo.

A profundidade segue o nível do aluno. No nível baixo, antes do primeiro módulo
que entra de uma trilha do catálogo, entram os módulos anteriores dela,
marcados como `base`: quem está começando não pula o "Iniciando no Python" para
cair direto em funções. Nos níveis médio e alto, só o que cobre os assuntos.

O desbloqueio dos passos dentro da trilha guiada é de `services/progresso.py`,
que usa `modulos_em_ordem` daqui.
"""

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    AssuntoEmenta,
    DisciplinaEmenta,
    Ementa,
    Lacuna,
    Modulo,
    NivelExperiencia,
    StatusAssuntos,
    Usuario,
)


@dataclass
class Item:
    disciplina: str
    periodo: int | None
    # Os assuntos da ementa que o item cobre. Vazio num módulo `base`.
    assuntos: list[str] = field(default_factory=list)
    modulo: Modulo | None = None
    lacuna: Lacuna | None = None
    # Entrou pelo nível baixo, como pré-requisito, e não por um assunto.
    base: bool = False


def ementa_confirmada(db: Session, usuario_id: int) -> Ementa | None:
    """A ementa que o aluno confirmou por último, com os assuntos lidos."""
    return db.scalars(
        select(Ementa)
        .where(
            Ementa.usuario_id == usuario_id,
            Ementa.confirmada_em.is_not(None),
            Ementa.status_assuntos == StatusAssuntos.prontos,
        )
        .order_by(Ementa.confirmada_em.desc(), Ementa.id.desc())
        .limit(1)
        .options(
            selectinload(Ementa.disciplinas)
            .selectinload(DisciplinaEmenta.assuntos)
            .options(
                selectinload(AssuntoEmenta.modulo).selectinload(Modulo.trilha),
                selectinload(AssuntoEmenta.lacuna),
            )
        )
    ).first()


def montar(db: Session, usuario: Usuario) -> tuple[Ementa | None, list[Item]]:
    """A ementa confirmada e os itens da trilha guiada, em ordem. Sem ementa, nada."""
    ementa = ementa_confirmada(db, usuario.id)
    if ementa is None:
        return None, []

    itens: list[Item] = []
    por_modulo: dict[int, Item] = {}
    por_lacuna: dict[int, Item] = {}
    # Só as de programação (marcadas na leitura ou pelo aluno), do 1º período em diante.
    disciplinas = sorted(
        (d for d in ementa.disciplinas if d.na_trilha), key=lambda d: (d.periodo or 99, d.ordem)
    )

    for disciplina in disciplinas:
        for assunto in disciplina.assuntos:
            if assunto.modulo is not None:
                item = por_modulo.get(assunto.modulo.id)
                if item is None:
                    if usuario.nivel_experiencia is NivelExperiencia.baixo:
                        _incluir_base(itens, por_modulo, disciplina, assunto.modulo)
                    item = Item(disciplina.nome, disciplina.periodo, modulo=assunto.modulo)
                    por_modulo[assunto.modulo.id] = item
                    itens.append(item)
                item.assuntos.append(assunto.texto)
                # Entrou como pré-requisito de outro, mas a ementa também o pede.
                item.base = False
            elif assunto.lacuna is not None:
                item = por_lacuna.get(assunto.lacuna.id)
                if item is None:
                    item = Item(disciplina.nome, disciplina.periodo, lacuna=assunto.lacuna)
                    por_lacuna[assunto.lacuna.id] = item
                    itens.append(item)
                item.assuntos.append(assunto.texto)
            # Sem um nem outro é um módulo apagado depois da leitura: o assunto
            # some da trilha até a próxima leitura o ligar de novo.
    return ementa, itens


def modulos_em_ordem(db: Session, usuario: Usuario) -> list[int]:
    """Os ids dos módulos da trilha guiada, na ordem em que o aluno os estuda."""
    _, itens = montar(db, usuario)
    return [item.modulo.id for item in itens if item.modulo is not None]


def _incluir_base(
    itens: list[Item], por_modulo: dict[int, Item], disciplina: DisciplinaEmenta, modulo: Modulo
) -> None:
    anteriores = sorted(
        (m for m in modulo.trilha.modulos if m.ordem < modulo.ordem), key=lambda m: m.ordem
    )
    for anterior in anteriores:
        if anterior.id in por_modulo:
            continue
        item = Item(disciplina.nome, disciplina.periodo, modulo=anterior, base=True)
        por_modulo[anterior.id] = item
        itens.append(item)
