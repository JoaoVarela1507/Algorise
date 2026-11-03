"""Log de auditoria das ações sensíveis (#39).

Login (certo e errado), troca de senha, exclusão de conta e, quando existir, a
emissão de certificado. Cada evento é uma linha no logger `app.auditoria`, com
o nome do evento em `evento` e o aluno em `usuario_id`: o agregador separa a
auditoria do resto filtrando pelo logger.

Nunca entra senha nem token; o e-mail de um login errado entra só como os
primeiros caracteres, para dar para seguir uma tentativa em massa sem guardar
o endereço de quem errou a senha.
"""

import logging
from typing import Any

logger = logging.getLogger("app.auditoria")


def registrar(evento: str, *, usuario_id: int | None = None, **dados: Any) -> None:
    logger.info(evento, extra={"evento": evento, "alvo_usuario_id": usuario_id, **dados})


def email_parcial(email: str) -> str:
    """`ana.lima@ufrpe.br` -> `an***@ufrpe.br`."""
    nome, _, dominio = email.partition("@")
    return f"{nome[:2]}***@{dominio}" if dominio else "***"
