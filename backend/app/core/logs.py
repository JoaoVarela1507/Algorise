"""Logs estruturados: uma linha JSON por evento, com a requisição e o aluno (#39).

Toda linha leva o `request_id`, a rota e o id do aluno da requisição em curso,
sem quem loga precisar passar isso: o middleware de rastreio e a dependência
de autenticação guardam os três em `ContextVar`s, e o formatador os lê. Assim
um `grep` pelo `request_id` do erro que o aluno viu traz tudo o que aconteceu
naquela requisição.

`LOG_FORMATO=json` em produção (o padrão lá), para o agregador indexar os
campos; `texto` em desenvolvimento, para ler no terminal.

**O que nunca vai para o log**: senha, token e o conteúdo das mensagens do
chat. `FiltroDeSegredos` apaga, antes de qualquer formatador, os campos com
esses nomes e o que tem cara de token (`Bearer ...`, JWT) no meio do texto.
"""

import json
import logging
import logging.config
import re
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
rota: ContextVar[str | None] = ContextVar("rota", default=None)
usuario_id: ContextVar[int | None] = ContextVar("usuario_id", default=None)

APAGADO = "[apagado]"
# Nome de campo que nunca sai do processo com o valor.
_CAMPO_SECRETO = re.compile(
    r"senha|password|token|secret|segredo|authorization|cookie|conteudo|mensagem_chat",
    re.IGNORECASE,
)
# O que tem cara de credencial no meio de um texto livre.
_TOKEN_NO_TEXTO = re.compile(
    r"(Bearer\s+)[\w.~+/=-]+|eyJ[\w-]+\.[\w-]+\.[\w-]+",
    re.IGNORECASE,
)
# Atributos que todo `LogRecord` tem: o que sobra é o `extra` de quem logou.
_PADRAO = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime", "taskName"}


def apagar_segredos(texto: str) -> str:
    return _TOKEN_NO_TEXTO.sub(lambda m: f"{m.group(1) or ''}{APAGADO}", texto)


class FiltroDeSegredos(logging.Filter):
    """Apaga senha, token e conteúdo do chat do registro, antes de formatar."""

    def filter(self, registro: logging.LogRecord) -> bool:
        # Sobre a mensagem já montada: um "Bearer %s" com o token no argumento
        # só vira credencial visível depois de juntar os dois.
        registro.msg = apagar_segredos(registro.getMessage())
        registro.args = None
        for campo in set(registro.__dict__) - _PADRAO:
            if _CAMPO_SECRETO.search(campo):
                setattr(registro, campo, APAGADO)
        return True


class FormatoJson(logging.Formatter):
    """Uma linha JSON: hora, nível, logger, mensagem, contexto da requisição e extras."""

    def format(self, registro: logging.LogRecord) -> str:
        linha: dict[str, Any] = {
            "ts": datetime.fromtimestamp(registro.created, UTC).isoformat(),
            "nivel": registro.levelname,
            "logger": registro.name,
            "mensagem": registro.getMessage(),
            "request_id": request_id.get(),
            "rota": rota.get(),
            "usuario_id": usuario_id.get(),
        }
        for campo in set(registro.__dict__) - _PADRAO:
            linha[campo] = registro.__dict__[campo]
        if registro.exc_info:
            linha["erro"] = apagar_segredos(self.formatException(registro.exc_info))
        return json.dumps(
            {k: v for k, v in linha.items() if v is not None}, ensure_ascii=False, default=str
        )


class FormatoTexto(logging.Formatter):
    """Para o terminal de desenvolvimento, com o `request_id` quando houver."""

    def format(self, registro: logging.LogRecord) -> str:
        base = super().format(registro)
        rid = request_id.get()
        return f"{base} [{rid}]" if rid else base


def configurar(formato: str, nivel: str = "INFO") -> None:
    """Liga o formato e o filtro em todo log da aplicação, inclusive o do uvicorn."""
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {"segredos": {"()": FiltroDeSegredos}},
            "formatters": {
                "json": {"()": FormatoJson},
                "texto": {
                    "()": FormatoTexto,
                    "format": "%(levelname)s %(name)s: %(message)s",
                },
            },
            "handlers": {
                "saida": {
                    "class": "logging.StreamHandler",
                    "formatter": formato,
                    "filters": ["segredos"],
                }
            },
            "root": {"handlers": ["saida"], "level": nivel},
            # O uvicorn tem handlers próprios: passam a usar o mesmo, e a linha
            # de acesso dele sai, porque o rastreio já loga cada requisição.
            "loggers": {
                "uvicorn": {"handlers": ["saida"], "level": nivel, "propagate": False},
                "uvicorn.error": {"handlers": ["saida"], "level": nivel, "propagate": False},
                "uvicorn.access": {"handlers": [], "level": "WARNING", "propagate": False},
            },
        }
    )
