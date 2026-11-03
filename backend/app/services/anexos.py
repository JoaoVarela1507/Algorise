"""Anexos do chat (#33): validar, guardar e levar o texto para o modelo.

O tipo sai do conteúdo, não da extensão nem do `Content-Type` do navegador:

| Tipo     | Como é reconhecido                                  | Vai para o modelo   |
| -------- | --------------------------------------------------- | ------------------- |
| `pdf`    | começa com `%PDF-` e o pypdf consegue ler           | o texto das páginas |
| `imagem` | o Pillow abre como PNG, JPEG ou WebP                | só o nome           |
| `texto`  | extensão de texto ou código, UTF-8 e sem byte nulo  | o conteúdo          |

O modelo do chat não lê imagem: ela fica guardada para o aluno, e o tutor só
sabe que ela existe.

O arquivo fica em `diretorio_midia/chat`, fora da pasta pública, com um nome
sorteado: o nome que o aluno deu só aparece na tela e no download.

Um anexo é de um aluno só e se liga a uma mensagem só. Apagar a conversa apaga
as mensagens, os anexos (cascade no banco) e os arquivos.
"""

import logging
import secrets
from io import BytesIO
from pathlib import Path
from typing import Final

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from pypdf.errors import PyPdfError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AnexoChat, MensagemChat, Usuario

logger = logging.getLogger(__name__)

EXTENSOES_DE_TEXTO: Final = {
    ".txt", ".md", ".csv", ".json", ".py", ".ipynb", ".c", ".h", ".cpp", ".java",
    ".js", ".ts", ".html", ".css", ".sql", ".sh", ".yml", ".yaml",
}  # fmt: skip
FORMATOS_DE_IMAGEM: Final = {"PNG", "JPEG", "WEBP"}
PAGINAS_DO_PDF: Final = 30


class AnexoInvalido(Exception):
    """O arquivo não é de um tipo aceito. A mensagem vai para o aluno."""


class AnexoGrandeDemais(Exception):
    """Passa de `chat_anexo_tamanho_maximo`."""


class AnexoNaoEncontrado(Exception):
    """Não existe, é de outro aluno ou já está em outra mensagem."""


def diretorio() -> Path:
    return Path(settings.diretorio_midia) / "chat"


def salvar(db: Session, usuario: Usuario, nome: str, conteudo: bytes) -> AnexoChat:
    if len(conteudo) > settings.chat_anexo_tamanho_maximo:
        raise AnexoGrandeDemais
    if not conteudo:
        raise AnexoInvalido("O arquivo está vazio.")
    nome = Path(nome or "anexo").name[:200]
    tipo, texto = _reconhecer(nome, conteudo)

    arquivo = secrets.token_hex(16)
    diretorio().mkdir(parents=True, exist_ok=True)
    (diretorio() / arquivo).write_bytes(conteudo)
    anexo = AnexoChat(
        usuario_id=usuario.id,
        nome=nome,
        tipo=tipo,
        tamanho=len(conteudo),
        arquivo=arquivo,
        texto=texto[: settings.chat_anexo_texto_maximo] if texto else None,
    )
    db.add(anexo)
    db.commit()
    return anexo


def do_aluno(db: Session, usuario_id: int, anexo_id: int) -> AnexoChat:
    anexo = db.get(AnexoChat, anexo_id)
    if anexo is None or anexo.usuario_id != usuario_id:
        raise AnexoNaoEncontrado
    return anexo


def soltos(db: Session, usuario_id: int, ids: list[int]) -> list[AnexoChat]:
    """Os anexos pedidos, todos do aluno e ainda sem mensagem, na ordem pedida."""
    unicos = list(dict.fromkeys(ids))
    if len(unicos) > settings.chat_anexos_por_mensagem:
        raise AnexoInvalido(f"Mande até {settings.chat_anexos_por_mensagem} anexos por mensagem.")
    encontrados = {
        anexo.id: anexo
        for anexo in db.scalars(
            select(AnexoChat).where(
                AnexoChat.id.in_(unicos),
                AnexoChat.usuario_id == usuario_id,
                AnexoChat.mensagem_id.is_(None),
            )
        )
    }
    if len(encontrados) != len(unicos):
        raise AnexoNaoEncontrado
    return [encontrados[i] for i in unicos]


def vincular(db: Session, anexos: list[AnexoChat], mensagem: MensagemChat) -> None:
    for anexo in anexos:
        anexo.mensagem_id = mensagem.id
    db.commit()


def para_o_modelo(pergunta: str, anexos: list[AnexoChat]) -> str:
    """A pergunta com o texto dos anexos embaixo, cada um com o nome."""
    partes = [pergunta]
    for anexo in anexos:
        if anexo.texto:
            partes.append(f'Anexo "{anexo.nome}":\n```\n{anexo.texto}\n```')
        else:
            partes.append(f'(O aluno anexou "{anexo.nome}", que você não consegue ler.)')
    return "\n\n".join(partes)


def caminho(anexo: AnexoChat) -> Path:
    return diretorio() / anexo.arquivo


def apagar(db: Session, anexo: AnexoChat) -> None:
    arquivo = anexo.arquivo
    db.delete(anexo)
    db.commit()
    apagar_arquivos([arquivo])


def apagar_arquivos(arquivos: list[str]) -> None:
    """Apaga do disco, pelo `AnexoChat.arquivo`. Chame depois do commit."""
    for arquivo in arquivos:
        try:
            (diretorio() / arquivo).unlink(missing_ok=True)
        except OSError:
            logger.warning("Não consegui apagar o anexo %s do disco", arquivo)


def _reconhecer(nome: str, conteudo: bytes) -> tuple[str, str | None]:
    if conteudo.startswith(b"%PDF-"):
        return "pdf", _texto_do_pdf(conteudo)
    imagem = _formato_de_imagem(conteudo)
    if imagem is not None:
        return "imagem", None
    if Path(nome).suffix.lower() in EXTENSOES_DE_TEXTO and b"\x00" not in conteudo:
        try:
            return "texto", conteudo.decode("utf-8")
        except UnicodeDecodeError as erro:
            raise AnexoInvalido("O arquivo de texto precisa estar em UTF-8.") from erro
    raise AnexoInvalido("Mande um arquivo de texto ou código, um PDF ou uma imagem.")


def _texto_do_pdf(conteudo: bytes) -> str:
    try:
        leitor = PdfReader(BytesIO(conteudo))
        paginas = leitor.pages[:PAGINAS_DO_PDF]
        return "\n".join((pagina.extract_text() or "") for pagina in paginas).strip()
    except (PyPdfError, ValueError, KeyError) as erro:
        raise AnexoInvalido("Não consegui ler esse PDF.") from erro


def _formato_de_imagem(conteudo: bytes) -> str | None:
    try:
        with Image.open(BytesIO(conteudo)) as imagem:
            formato = imagem.format
            imagem.verify()
    except (UnidentifiedImageError, OSError, SyntaxError):
        return None
    return formato if formato in FORMATOS_DE_IMAGEM else None
