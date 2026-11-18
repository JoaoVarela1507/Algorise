"""Linha de comando do vault. Ver o docstring de `app.ia.vault`."""

import argparse
import asyncio
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import select

from app.core.database import SessionLocal
from app.ia import IAIndisponivel, get_provedor_ia_tarefas
from app.ia.vault import (
    Ingestao,
    ModuloNaoEncontrado,
    ingerir_transcricao,
    registrar_modulos,
    registrar_prompts,
)
from app.ia.vault.ingestao import ingerir_falas_do_modulo, reembeddar
from app.models import DocumentoVault, Modulo
from app.services import transcricao


def main(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.ia.vault")
    comandos = parser.add_subparsers(dest="comando", required=True)

    ingerir = comandos.add_parser("ingerir", help="grava a transcrição do vídeo de um módulo")
    ingerir.add_argument("--modulo", type=int, required=True, help="id do módulo")
    ingerir.add_argument("arquivo", type=Path, help=".srt, .vtt ou .txt, em UTF-8")

    comandos.add_parser("registrar-modulos", help="grava o texto dos módulos do catálogo")
    comandos.add_parser("registrar-prompts", help="grava os prompts das skills")
    comandos.add_parser(
        "reembeddar", help="refaz os vetores de todo o vault com o provedor de embedding atual"
    )
    transcrever = comandos.add_parser(
        "transcrever",
        help="transcreve o vídeo do YouTube do módulo (legenda ou Whisper) e grava no vault",
    )
    transcrever.add_argument(
        "--modulo", type=int, help="id do módulo; sem ele, todo módulo com vídeo e sem transcrição"
    )

    args = parser.parse_args(argumentos)
    try:
        return asyncio.run(_executar(args))
    except (IAIndisponivel, ModuloNaoEncontrado) as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1


async def _executar(args: argparse.Namespace) -> int:
    provedor = get_provedor_ia_tarefas()
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
        elif args.comando == "transcrever":
            await _transcrever(sessao, provedor, args.modulo)
        elif args.comando == "reembeddar":
            print(f"{await reembeddar(sessao, provedor)} trechos com vetor novo")
        else:
            registrar = (
                registrar_modulos if args.comando == "registrar-modulos" else registrar_prompts
            )
            for ingestao in await registrar(sessao, provedor):
                _relatar(ingestao)
    return 0


async def _transcrever(sessao, provedor, modulo_id: int | None) -> None:
    """A transcrição do vídeo inteiro do módulo, para o painel do passo e para o RAG.

    Módulo que é um trecho de uma aula longa (`inicio_segundos`) fica de fora: a
    transcrição dele vem da do vídeo de origem, pela tarefa de transcrição (#208).
    """
    if modulo_id is not None:
        modulo = sessao.get(Modulo, modulo_id)
        if modulo is None:
            raise ModuloNaoEncontrado(f"Módulo {modulo_id} não existe")
        modulos = [modulo]
    else:
        ja_tem = select(DocumentoVault.modulo_id).where(DocumentoVault.chave.like("modulo:%"))
        modulos = list(
            sessao.scalars(
                select(Modulo).where(
                    Modulo.video_url.is_not(None),
                    Modulo.inicio_segundos.is_(None),
                    Modulo.id.not_in(ja_tem.where(DocumentoVault.modulo_id.is_not(None))),
                )
            )
        )
    for modulo in modulos:
        youtube_id = transcricao.id_do_video(modulo.video_url)
        if youtube_id is None:
            print(f"módulo {modulo.id}: o vídeo não é do YouTube, pulado")
            continue
        print(f"módulo {modulo.id} ({modulo.titulo}): transcrevendo {youtube_id}...", flush=True)
        with TemporaryDirectory(prefix="algorise-video-") as pasta:
            try:
                falas, fonte = transcricao.falas_do_video(youtube_id, Path(pasta))
            except transcricao.VideoIndisponivel as erro:
                print(f"módulo {modulo.id}: vídeo indisponível ({erro})")
                continue
        if not falas:
            print(f"módulo {modulo.id}: sem fala para transcrever")
            continue
        _relatar(await ingerir_falas_do_modulo(sessao, provedor, modulo, falas))
        print(f"  {len(falas)} falas, pela {fonte}")


def _relatar(ingestao: Ingestao) -> None:
    documento = ingestao.documento
    if ingestao.alterado:
        print(f"{documento.chave}: versão {documento.versao}, {len(documento.trechos)} trechos")
    else:
        print(f"{documento.chave}: sem mudança (versão {documento.versao})")


if __name__ == "__main__":
    sys.exit(main())
