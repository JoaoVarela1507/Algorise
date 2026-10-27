"""Entrada de conteúdo no vault: transcrições, módulos do catálogo e prompts das skills."""

import hashlib
import importlib
import pkgutil
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ia import skills
from app.ia.base import ProvedorIA
from app.ia.vault.trechos import Fala, Trecho, dividir, ler_transcricao
from app.models import DocumentoVault, Modulo, OrigemVault, TrechoVault, Trilha

# Quantos trechos vão num pedido de embedding. Uma transcrição longa num pedido
# só pode passar do timeout de leitura do Ollama.
LOTE_DE_EMBEDDING = 32


class ModuloNaoEncontrado(Exception):
    pass


@dataclass(frozen=True)
class Ingestao:
    documento: DocumentoVault
    # `False` quando o conteúdo era o mesmo já guardado e nada foi refeito.
    alterado: bool


async def ingerir_transcricao(
    sessao: Session, provedor: ProvedorIA, *, modulo_id: int, conteudo: str, nome_arquivo: str
) -> Ingestao:
    """Grava a transcrição do vídeo do módulo, substituindo a anterior, se houver."""
    modulo = sessao.get(Modulo, modulo_id)
    if modulo is None:
        raise ModuloNaoEncontrado(f"Módulo {modulo_id} não existe")
    return await _ingerir(
        sessao,
        provedor,
        chave=f"modulo:{modulo_id}",
        origem=OrigemVault.transcricao,
        titulo=modulo.titulo,
        conteudo=conteudo,
        trechos=dividir(ler_transcricao(conteudo, nome_arquivo)),
        modulo_id=modulo_id,
    )


async def registrar_modulos(sessao: Session, provedor: ProvedorIA) -> list[Ingestao]:
    """Grava no vault o texto de cada módulo do catálogo: disciplina, trilha, título e descrição.

    É o que deixa um assunto de ementa (#38) achar o módulo que o cobre antes de
    o vídeo dele ser transcrito. Só o módulo novo ou alterado pede embedding, e
    o documento de um módulo apagado vai junto com ele (cascade).
    """
    modulos = sessao.scalars(
        select(Modulo).join(Modulo.trilha).options(selectinload(Modulo.trilha)).order_by(Modulo.id)
    ).all()
    ingestoes = []
    for modulo in modulos:
        conteudo = texto_do_modulo(modulo.trilha, modulo)
        ingestoes.append(
            await _ingerir(
                sessao,
                provedor,
                chave=f"descricao:modulo:{modulo.id}",
                origem=OrigemVault.modulo,
                titulo=modulo.titulo,
                conteudo=conteudo,
                trechos=dividir([Fala(conteudo)]),
                modulo_id=modulo.id,
            )
        )
    return ingestoes


def texto_do_modulo(trilha: Trilha, modulo: Modulo) -> str:
    linhas = [f"{trilha.disciplina}: {trilha.nome}", modulo.titulo]
    if modulo.descricao:
        linhas.append(modulo.descricao)
    return "\n".join(linhas)


async def registrar_prompts(sessao: Session, provedor: ProvedorIA) -> list[Ingestao]:
    """Grava no vault o `PROMPT` de cada skill de `app/ia/skills/`.

    O prompt continua vivendo no código, que é o que os testes cobrem; o vault
    guarda a cópia com versão, para as skills consultarem. Rodar de novo sem
    mudança no prompt não refaz nada.
    """
    ingestoes = []
    for info in pkgutil.iter_modules(skills.__path__):
        modulo = importlib.import_module(f"{skills.__name__}.{info.name}")
        prompt = getattr(modulo, "PROMPT", None)
        if not isinstance(prompt, str):
            continue
        ingestoes.append(
            await _ingerir(
                sessao,
                provedor,
                chave=f"skill:{info.name}",
                origem=OrigemVault.prompt,
                titulo=f"Prompt da skill {info.name}",
                conteudo=prompt,
                trechos=dividir([Fala(prompt)]),
                skill=info.name,
            )
        )
    return ingestoes


async def _ingerir(
    sessao: Session,
    provedor: ProvedorIA,
    *,
    chave: str,
    origem: OrigemVault,
    titulo: str,
    conteudo: str,
    trechos: list[Trecho],
    modulo_id: int | None = None,
    skill: str | None = None,
) -> Ingestao:
    hash_conteudo = hashlib.sha256(conteudo.encode()).hexdigest()
    documento = sessao.scalar(select(DocumentoVault).where(DocumentoVault.chave == chave))
    if documento is not None and documento.hash_conteudo == hash_conteudo:
        return Ingestao(documento, alterado=False)

    # Os vetores vêm antes de mexer no banco: se o provedor cair no meio, a
    # versão anterior continua inteira.
    vetores: list[list[float]] = []
    for inicio in range(0, len(trechos), LOTE_DE_EMBEDDING):
        lote = trechos[inicio : inicio + LOTE_DE_EMBEDDING]
        vetores.extend(await provedor.embeddings([t.texto for t in lote]))

    if documento is None:
        documento = DocumentoVault(chave=chave, origem=origem, versao=1)
        sessao.add(documento)
    else:
        documento.versao += 1
        documento.trechos.clear()
        # Apaga os trechos antigos antes de inserir os novos, que reusam as
        # mesmas `ordem` (únicas por documento).
        sessao.flush()
    documento.titulo = titulo
    documento.hash_conteudo = hash_conteudo
    documento.modulo_id = modulo_id
    documento.skill = skill
    documento.trechos = [
        TrechoVault(ordem=i, texto=t.texto, inicio_segundos=t.inicio, embedding=v)
        for i, (t, v) in enumerate(zip(trechos, vetores, strict=True))
    ]
    sessao.commit()
    return Ingestao(documento, alterado=True)
