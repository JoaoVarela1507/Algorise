"""Gestão de trilhas, passos e atividades sem migração nem deploy (#41).

Três regras protegem quem já está estudando:

- **progresso não se apaga:** passo ou trilha com progresso de aluno, ou
  atividade com resposta, não pode ser apagado (`ConteudoComProgresso`). Para
  tirar do ar, despublica-se. Mover e editar pode: o progresso é do passo (o
  módulo), não da posição dele;
- **trilha publicada fica válida:** publicar confere o gabarito de cada
  atividade (`problemas`), e editar uma atividade de trilha publicada passa
  pela mesma conferência;
- **a ordem não tem buraco:** inserir, mover e apagar renumeram os vizinhos,
  porque o "próximo passo" é a ordem mais um.
"""

from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Atividade,
    Modulo,
    Parceiro,
    ProgressoUsuario,
    RespostaUsuario,
    StatusProgresso,
    TipoAtividade,
    Trilha,
)
from app.schemas.admin import (
    AtividadeCriacao,
    AtividadeEdicao,
    ErroComum,
    MetricasAtividade,
    MetricasTrilha,
    ParceiroCriacao,
    PassoCriacao,
    PassoEdicao,
    ProblemaDeConteudo,
    TrilhaCriacao,
    TrilhaEdicao,
    TrilhaImportada,
)
from app.services import trilhas as servico_trilhas


class SlugEmUso(Exception):
    pass


class ParceiroNaoEncontrado(Exception):
    pass


class ConteudoComProgresso(Exception):
    """Apagar levaria junto o progresso ou as respostas de alunos."""


class ConteudoInvalido(Exception):
    def __init__(self, problemas: list[ProblemaDeConteudo]) -> None:
        super().__init__(f"{len(problemas)} problemas")
        self.problemas = problemas


# --- leitura ------------------------------------------------------------------------------


def listar(db: Session) -> list[Trilha]:
    """Todas as trilhas, publicadas e rascunhos, com passos e atividades."""
    return list(
        db.scalars(
            select(Trilha)
            .order_by(Trilha.periodo, Trilha.nome)
            .options(selectinload(Trilha.modulos).selectinload(Modulo.atividades))
        )
    )


# --- trilhas ------------------------------------------------------------------------------


def criar_trilha(db: Session, dados: TrilhaCriacao) -> Trilha:
    if db.scalar(select(Trilha.id).where(Trilha.slug == dados.slug)) is not None:
        raise SlugEmUso(dados.slug)
    _conferir_parceiro(db, dados.parceiro_id)
    # Nasce rascunho: publicar é um passo à parte, que confere o conteúdo.
    trilha = Trilha(**dados.model_dump(), publicada=False)
    db.add(trilha)
    db.commit()
    return trilha


def editar_trilha(db: Session, trilha: Trilha, dados: TrilhaEdicao) -> Trilha:
    campos = dados.model_dump(exclude_unset=True)
    _conferir_parceiro(db, campos.get("parceiro_id"))
    for campo, valor in campos.items():
        setattr(trilha, campo, valor)
    db.commit()
    servico_trilhas.invalidar_catalogo()
    return trilha


def apagar_trilha(db: Session, trilha: Trilha) -> None:
    if _tem_progresso(db, trilha_id=trilha.id):
        raise ConteudoComProgresso
    db.delete(trilha)
    db.commit()
    servico_trilhas.invalidar_catalogo()


def publicar(db: Session, trilha: Trilha, publicada: bool) -> Trilha:
    """Publica conferindo o conteúdo; despublicar não confere nada."""
    if publicada and (achados := problemas(trilha)):
        raise ConteudoInvalido(achados)
    trilha.publicada = publicada
    db.commit()
    servico_trilhas.invalidar_catalogo()
    return trilha


def problemas(trilha: Trilha) -> list[ProblemaDeConteudo]:
    """O que impede a trilha de ir ao ar: sem passo ou atividade sem gabarito."""
    if not trilha.modulos:
        return [ProblemaDeConteudo(problema="A trilha não tem nenhum passo.")]
    return [
        ProblemaDeConteudo(passo=passo.ordem, atividade=atividade.ordem, problema=problema)
        for passo in sorted(trilha.modulos, key=lambda m: m.ordem)
        for atividade in passo.atividades
        if (problema := problema_da_atividade(atividade))
    ]


def problema_da_atividade(atividade: Atividade) -> str | None:
    """Sem o gabarito, a correção (#30) não tem com o que comparar."""
    if atividade.tipo is TipoAtividade.terminal:
        if not (atividade.comando_esperado or "").strip():
            return "A atividade de terminal precisa do comando esperado."
        if not (atividade.saida_esperada or "").strip():
            return "A atividade de terminal precisa da saída esperada."
        return None
    if not (atividade.resposta_esperada or "").strip():
        return "A atividade precisa da resposta esperada."
    return None


# --- passos -------------------------------------------------------------------------------


def criar_passo(db: Session, trilha: Trilha, dados: PassoCriacao) -> Modulo:
    total = len(trilha.modulos)
    ordem = min(dados.ordem or total + 1, total + 1)
    _abrir_espaco(db, trilha, ordem)
    passo = Modulo(trilha_id=trilha.id, ordem=ordem, **dados.model_dump(exclude={"ordem"}))
    db.add(passo)
    db.commit()
    db.refresh(trilha)
    servico_trilhas.invalidar_catalogo()
    return passo


def editar_passo(db: Session, passo: Modulo, dados: PassoEdicao) -> Modulo:
    campos = dados.model_dump(exclude_unset=True)
    nova_ordem = campos.pop("ordem", None)
    for campo, valor in campos.items():
        setattr(passo, campo, valor)
    if nova_ordem is not None and nova_ordem != passo.ordem:
        _mover(db, passo, nova_ordem)
    db.commit()
    servico_trilhas.invalidar_catalogo()
    return passo


def apagar_passo(db: Session, passo: Modulo) -> None:
    if _tem_progresso(db, modulo_id=passo.id):
        raise ConteudoComProgresso
    trilha, ordem = passo.trilha, passo.ordem
    db.delete(passo)
    db.flush()
    _fechar_espaco(db, trilha, ordem, sem=passo)
    db.commit()
    servico_trilhas.invalidar_catalogo()


# --- atividades ---------------------------------------------------------------------------


def criar_atividade(db: Session, passo: Modulo, dados: AtividadeCriacao) -> Atividade:
    ordem = dados.ordem or (max((a.ordem for a in passo.atividades), default=0) + 1)
    campos = dados.model_dump(exclude={"passo_id", "ordem"}, exclude_none=True)
    for existente in sorted(passo.atividades, key=lambda a: -a.ordem):
        if existente.ordem >= ordem:
            existente.ordem += 1
            db.flush()
    atividade = Atividade(modulo_id=passo.id, ordem=ordem, **campos)
    db.add(atividade)
    _conferir_se_publicada(db, passo, atividade)
    db.commit()
    return atividade


def editar_atividade(db: Session, atividade: Atividade, dados: AtividadeEdicao) -> Atividade:
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(atividade, campo, valor)
    _conferir_se_publicada(db, atividade.modulo, atividade)
    db.commit()
    return atividade


def apagar_atividade(db: Session, atividade: Atividade) -> None:
    respondida = db.scalar(
        select(RespostaUsuario.id).where(RespostaUsuario.atividade_id == atividade.id).limit(1)
    )
    if respondida is not None:
        raise ConteudoComProgresso
    passo, ordem = atividade.modulo, atividade.ordem
    db.delete(atividade)
    db.flush()
    for seguinte in sorted(passo.atividades, key=lambda a: a.ordem):
        if seguinte is not atividade and seguinte.ordem > ordem:
            seguinte.ordem -= 1
            db.flush()
    db.commit()


# --- importação ---------------------------------------------------------------------------


def importar(db: Session, dados: TrilhaImportada) -> Trilha:
    """Cria ou atualiza a trilha do slug, com passos e atividades pela posição.

    Passo que sobra na trilha e não veio no arquivo é apagado, se não tiver
    progresso; com progresso, a importação inteira é recusada.
    """
    trilha = db.scalar(select(Trilha).where(Trilha.slug == dados.slug))
    if trilha is None:
        trilha = Trilha(slug=dados.slug, publicada=False)
        db.add(trilha)
    for campo in ("nome", "disciplina", "categoria", "periodo", "descricao"):
        setattr(trilha, campo, getattr(dados, campo))
    db.flush()

    existentes = {passo.ordem: passo for passo in trilha.modulos}
    for ordem, dados_passo in enumerate(dados.passos, start=1):
        passo = existentes.pop(ordem, None)
        if passo is None:
            passo = Modulo(trilha_id=trilha.id, ordem=ordem)
            db.add(passo)
        for campo, valor in dados_passo.model_dump(exclude={"ordem", "atividades"}).items():
            setattr(passo, campo, valor)
        db.flush()
        atividades = {atividade.ordem: atividade for atividade in passo.atividades}
        for ordem_atividade, dados_atividade in enumerate(dados_passo.atividades, start=1):
            atividade = atividades.pop(ordem_atividade, None)
            if atividade is None:
                atividade = Atividade(modulo_id=passo.id, ordem=ordem_atividade)
                db.add(atividade)
            for campo, valor in dados_atividade.model_dump().items():
                if valor is not None or campo in ("dica", "comando_esperado", "saida_esperada"):
                    setattr(atividade, campo, valor)
        for sobra in atividades.values():
            db.delete(sobra)
    for sobra in existentes.values():
        if _tem_progresso(db, modulo_id=sobra.id):
            db.rollback()
            raise ConteudoComProgresso
        db.delete(sobra)
    db.flush()
    # As atividades novas entraram pelo `modulo_id`, não pela coleção do passo:
    # a conferência abaixo precisa ler tudo de novo do banco.
    db.expire_all()

    if dados.publicada and (achados := problemas(trilha)):
        db.rollback()
        raise ConteudoInvalido(achados)
    trilha.publicada = dados.publicada
    db.commit()
    servico_trilhas.invalidar_catalogo()
    return trilha


# --- métricas -----------------------------------------------------------------------------


def metricas(db: Session) -> list[MetricasTrilha]:
    """Conclusão por trilha e, por atividade, acerto, abandono e erros comuns no terminal."""
    resultado = []
    for trilha in listar(db):
        total_passos = len(trilha.modulos)
        concluidos_por_aluno = Counter(
            usuario_id
            for usuario_id, status in db.execute(
                select(ProgressoUsuario.usuario_id, ProgressoUsuario.status).where(
                    ProgressoUsuario.trilha_id == trilha.id
                )
            )
            if status is StatusProgresso.concluido
        )
        iniciaram = db.scalar(
            select(func.count(func.distinct(ProgressoUsuario.usuario_id))).where(
                ProgressoUsuario.trilha_id == trilha.id
            )
        )
        concluiram = sum(
            1 for n in concluidos_por_aluno.values() if total_passos and n >= total_passos
        )
        resultado.append(
            MetricasTrilha(
                trilha_id=trilha.id,
                slug=trilha.slug,
                nome=trilha.nome,
                publicada=trilha.publicada,
                alunos_iniciaram=iniciaram or 0,
                alunos_concluiram=concluiram,
                taxa_de_conclusao=round(concluiram / iniciaram, 3) if iniciaram else 0.0,
                atividades=[
                    _metricas_da_atividade(db, passo, atividade)
                    for passo in sorted(trilha.modulos, key=lambda m: m.ordem)
                    for atividade in passo.atividades
                ],
            )
        )
    return resultado


def _metricas_da_atividade(db: Session, passo: Modulo, atividade: Atividade) -> MetricasAtividade:
    respostas = db.execute(
        select(RespostaUsuario.usuario_id, RespostaUsuario.correta, RespostaUsuario.conteudo).where(
            RespostaUsuario.atividade_id == atividade.id
        )
    ).all()
    alunos = {usuario for usuario, _, _ in respostas}
    acertaram = {usuario for usuario, correta, _ in respostas if correta}
    acertos = sum(1 for _, correta, _ in respostas if correta)
    erros_comuns = []
    if atividade.tipo is TipoAtividade.terminal:
        erradas = Counter(conteudo.strip() for _, correta, conteudo in respostas if not correta)
        erros_comuns = [ErroComum(resposta=r, vezes=n) for r, n in erradas.most_common(3)]
    return MetricasAtividade(
        atividade_id=atividade.id,
        passo=passo.ordem,
        ordem=atividade.ordem,
        tipo=atividade.tipo,
        tentativas=len(respostas),
        alunos=len(alunos),
        acertos=acertos,
        taxa_de_acerto=round(acertos / len(respostas), 3) if respostas else 0.0,
        abandono=round(len(alunos - acertaram) / len(alunos), 3) if alunos else 0.0,
        erros_comuns=erros_comuns,
    )


# --- parceiros ----------------------------------------------------------------------------


def listar_parceiros(db: Session) -> list[Parceiro]:
    return list(db.scalars(select(Parceiro).order_by(Parceiro.nome)))


def criar_parceiro(db: Session, dados: ParceiroCriacao) -> Parceiro:
    parceiro = Parceiro(**dados.model_dump())
    db.add(parceiro)
    db.commit()
    return parceiro


def _conferir_parceiro(db: Session, parceiro_id: int | None) -> None:
    if parceiro_id is not None and db.get(Parceiro, parceiro_id) is None:
        raise ParceiroNaoEncontrado(parceiro_id)


# --- apoio --------------------------------------------------------------------------------


def _tem_progresso(
    db: Session, *, trilha_id: int | None = None, modulo_id: int | None = None
) -> bool:
    consulta = select(ProgressoUsuario.id)
    if trilha_id is not None:
        consulta = consulta.where(ProgressoUsuario.trilha_id == trilha_id)
    if modulo_id is not None:
        consulta = consulta.where(ProgressoUsuario.modulo_id == modulo_id)
    return db.scalar(consulta.limit(1)) is not None


def _conferir_se_publicada(db: Session, passo: Modulo, atividade: Atividade) -> None:
    if passo.trilha.publicada and (problema := problema_da_atividade(atividade)):
        db.rollback()
        raise ConteudoInvalido(
            [ProblemaDeConteudo(passo=passo.ordem, atividade=atividade.ordem, problema=problema)]
        )


def _abrir_espaco(db: Session, trilha: Trilha, ordem: int) -> None:
    """Empurra uma posição os passos de `ordem` em diante, do último para o primeiro."""
    for passo in sorted(trilha.modulos, key=lambda m: -m.ordem):
        if passo.ordem >= ordem:
            passo.ordem += 1
            db.flush()


def _fechar_espaco(db: Session, trilha: Trilha, ordem: int, *, sem: Modulo) -> None:
    for passo in sorted(trilha.modulos, key=lambda m: m.ordem):
        if passo is not sem and passo.ordem > ordem:
            passo.ordem -= 1
            db.flush()


def _mover(db: Session, passo: Modulo, destino: int) -> None:
    """Leva o passo para `destino`, deslocando os do caminho, sem colidir na unicidade."""
    trilha = passo.trilha
    destino = min(destino, len(trilha.modulos))
    origem = passo.ordem
    # Fora do caminho enquanto os outros andam: (trilha, ordem) é único.
    passo.ordem = 0
    db.flush()
    if destino > origem:
        for outro in sorted(trilha.modulos, key=lambda m: m.ordem):
            if outro is not passo and origem < outro.ordem <= destino:
                outro.ordem -= 1
                db.flush()
    else:
        for outro in sorted(trilha.modulos, key=lambda m: -m.ordem):
            if outro is not passo and destino <= outro.ordem < origem:
                outro.ordem += 1
                db.flush()
    passo.ordem = destino
    db.flush()
