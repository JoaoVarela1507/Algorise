"""Linha de comando do vault. Ver o docstring de `app.ia.vault`."""

import argparse
import asyncio
import sys
from pathlib import Path

from app.core.database import SessionLocal
from app.ia import IAIndisponivel, get_provedor_ia
from app.ia.vault import (
    Ingestao,
    ModuloNaoEncontrado,
    ingerir_transcricao,
    registrar_modulos,
    registrar_prompts,
)


def main(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.ia.vault")
    comandos = parser.add_subparsers(dest="comando", required=True)

    ingerir = comandos.add_parser("ingerir", help="grava a transcrição do vídeo de um módulo")
    ingerir.add_argument("--modulo", type=int, required=True, help="id do módulo")
    ingerir.add_argument("arquivo", type=Path, help=".srt, .vtt ou .txt, em UTF-8")

    comandos.add_parser("registrar-modulos", help="grava o texto dos módulos do catálogo")
    comandos.add_parser("registrar-prompts", help="grava os prompts das skills")

    args = parser.parse_args(argumentos)
    try:
        return asyncio.run(_executar(args))
    except (IAIndisponivel, ModuloNaoEncontrado) as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1


async def _executar(args: argparse.Namespace) -> int:
    provedor = get_provedor_ia()
    with SessionLocal() as sessao:
        if args.comando == "ingerir":
            ingestao = await ingerir_transcricao(
                sessao,
                provedor,
                modulo_id=args.modulo,
                conteudo=args.arquivo.read_text(encoding="utf-8"),
                nome_arquivo=args.arquivo.name,
            )
            _relatar(ingestao)
        else:
            registrar = (
                registrar_modulos if args.comando == "registrar-modulos" else registrar_prompts
            )
            for ingestao in await registrar(sessao, provedor):
                _relatar(ingestao)
    return 0


def _relatar(ingestao: Ingestao) -> None:
    documento = ingestao.documento
    if ingestao.alterado:
        print(f"{documento.chave}: versão {documento.versao}, {len(documento.trechos)} trechos")
    else:
        print(f"{documento.chave}: sem mudança (versão {documento.versao})")


if __name__ == "__main__":
    sys.exit(main())
