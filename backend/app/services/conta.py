"""Direitos do titular sobre a conta (LGPD, #40): exportar os dados e excluir a conta.

A exclusão tem prazo: o pedido desativa a conta na hora (sessões derrubadas, login
só reativa, some do ranking) e o expurgo apaga tudo depois de
`prazo_exclusao_dias`. O prazo protege contra exclusão por engano e contra quem
roubou a sessão; entrar de novo antes dele cancela.

O expurgo não precisa anonimizar nada hoje: todas as tabelas com dado do aluno
apagam em cascata junto com `usuarios`, e nenhuma delas guarda algo que a lei
obrigue a manter. Quando entrar a validação pública de certificados (#32), é lá
que se decide o que sobrevive à conta.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.seguranca import conferir_senha
from app.models import Base, Usuario
from app.services import ranking, sessoes

logger = logging.getLogger(__name__)

# O aluno digita isto para confirmar. Protege a conta só de OAuth, que não tem
# senha para pedir, de um clique acidental ou de um script num token vazado.
CONFIRMACAO_DE_EXCLUSAO = "EXCLUIR"

# Nunca sai da API, nem na exportação: é segredo do sistema, não dado do aluno.
_COLUNAS_OCULTAS = {"senha_hash"}


class ConfirmacaoInvalida(Exception):
    """Faltou digitar a confirmação ou a senha não confere."""


def exportar_dados(db: Session, usuario: Usuario) -> dict[str, Any]:
    """Tudo o que o Algorise guarda sobre o aluno, tabela por tabela.

    As tabelas são descobertas pelo mapeamento: toda tabela com `usuario_id`
    entra. Assim, uma tabela nova com dado do aluno aparece na exportação sem
    ninguém precisar lembrar de acrescentá-la aqui.
    """
    dados: dict[str, Any] = {
        "gerado_em": datetime.now(UTC).isoformat(),
        "conta": _linha(usuario),
    }

    for mapeador in sorted(Base.registry.mappers, key=lambda m: m.local_table.name):
        tabela = mapeador.local_table
        if "usuario_id" not in tabela.c or mapeador.class_ is Usuario:
            continue
        linhas = db.execute(
            select(mapeador.class_).where(tabela.c.usuario_id == usuario.id)
        ).scalars()
        dados[tabela.name] = [_linha(linha) for linha in linhas]

    return dados


def agendar_exclusao(
    db: Session, usuario: Usuario, *, confirmacao: str, senha: str | None
) -> datetime:
    """Desativa a conta e marca o expurgo. Devolve a data em que os dados somem."""
    if confirmacao.strip().upper() != CONFIRMACAO_DE_EXCLUSAO:
        raise ConfirmacaoInvalida("confirmação")
    # Conta com senha pede a senha: quem pegou um access token não apaga a
    # conta alheia só com ele.
    if usuario.senha_hash is not None and not conferir_senha(senha or "", usuario.senha_hash):
        raise ConfirmacaoInvalida("senha")

    usuario.exclusao_agendada_para = datetime.now(UTC) + timedelta(
        days=settings.prazo_exclusao_dias
    )
    db.commit()

    sessoes.revogar_sessoes_do_usuario(usuario.id)
    ranking.remover(usuario.id)
    return usuario.exclusao_agendada_para


def cancelar_exclusao_se_agendada(db: Session, usuario: Usuario) -> bool:
    """Chamado no login: se havia exclusão agendada, cancela. Devolve se cancelou."""
    if usuario.exclusao_agendada_para is None:
        return False

    usuario.exclusao_agendada_para = None
    db.commit()
    # O aluno volta ao ranking na próxima reconstrução do sorted set.
    ranking.invalidar()
    return True


def expurgar_vencidas(db: Session, *, agora: datetime | None = None) -> int:
    """Apaga de vez as contas cujo prazo de exclusão passou. Devolve quantas."""
    agora = agora or datetime.now(UTC)
    vencidas = (
        db.execute(select(Usuario).where(Usuario.exclusao_agendada_para <= agora)).scalars().all()
    )

    for usuario in vencidas:
        # Redis primeiro: se o banco falhar depois, sobra uma conta desativada
        # que o próximo expurgo apaga, e não uma sessão viva de conta apagada.
        sessoes.revogar_sessoes_do_usuario(usuario.id)
        ranking.remover(usuario.id)
        db.delete(usuario)

    db.commit()
    return len(vencidas)


def _linha(objeto: Any) -> dict[str, Any]:
    colunas = inspect(objeto).mapper.column_attrs
    return {
        coluna.key: _serializavel(getattr(objeto, coluna.key))
        for coluna in colunas
        if coluna.key not in _COLUNAS_OCULTAS
    }


def _serializavel(valor: Any) -> Any:
    if hasattr(valor, "isoformat"):  # datetime e date
        return valor.isoformat()
    if hasattr(valor, "value"):  # enums do domínio
        return valor.value
    if valor is None or isinstance(valor, str | int | float | bool | list | dict):
        return valor
    return str(valor)
