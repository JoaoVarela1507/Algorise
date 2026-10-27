"""Seed do catálogo acadêmico do onboarding (#28).

A UFRPE e o Bacharelado em Sistemas de Informação são o caso da persona. As
outras instituições de Recife entram sem cursos, só para o autocomplete ter com
o que comparar — um catálogo de uma instituição só não exercita a busca.

Idempotente: identifica a instituição pelo nome e o curso pelo par
(instituição, nome). Rodar de novo marca como verificado o que já existia sem a
marca (por exemplo, a UFRPE digitada por um aluno antes do seed).
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Curso, Instituicao

INSTITUICOES: list[dict] = [
    {
        "nome": "Universidade Federal Rural de Pernambuco",
        "sigla": "UFRPE",
        "uf": "PE",
        "cursos": [{"nome": "Bacharelado em Sistemas de Informação", "total_periodos": 8}],
    },
    {"nome": "Universidade Federal de Pernambuco", "sigla": "UFPE", "uf": "PE", "cursos": []},
    {"nome": "Universidade de Pernambuco", "sigla": "UPE", "uf": "PE", "cursos": []},
    {
        "nome": "Instituto Federal de Educação, Ciência e Tecnologia de Pernambuco",
        "sigla": "IFPE",
        "uf": "PE",
        "cursos": [],
    },
    {"nome": "Universidade Católica de Pernambuco", "sigla": "UNICAP", "uf": "PE", "cursos": []},
]


def aplicar(db: Session) -> int:
    """Grava o catálogo e devolve quantas instituições ele tem."""
    for dados in INSTITUICOES:
        instituicao = _por_nome(db, Instituicao, dados["nome"])
        if instituicao is None:
            instituicao = Instituicao(nome=dados["nome"])
            db.add(instituicao)
        instituicao.sigla = dados["sigla"]
        instituicao.uf = dados["uf"]
        instituicao.verificada = True
        db.flush()

        for dados_curso in dados["cursos"]:
            curso = _por_nome(db, Curso, dados_curso["nome"], instituicao_id=instituicao.id)
            if curso is None:
                curso = Curso(instituicao_id=instituicao.id, nome=dados_curso["nome"])
                db.add(curso)
            curso.total_periodos = dados_curso["total_periodos"]
            curso.verificado = True

    db.commit()
    return len(INSTITUICOES)


def _por_nome(db: Session, modelo, nome: str, **filtros):
    # Sem caixa, como o perfil compara: a "ufrpe" de um aluno é a mesma linha.
    consulta = select(modelo).where(func.lower(modelo.nome) == nome.lower())
    for campo, valor in filtros.items():
        consulta = consulta.where(getattr(modelo, campo) == valor)
    return db.execute(consulta).scalar_one_or_none()
