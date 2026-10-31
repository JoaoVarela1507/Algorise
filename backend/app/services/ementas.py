"""Ementa em PDF do onboarding (telas 14 e 15): receber, guardar e extrair o texto.

O fluxo tem duas metades, separadas de propósito:

1. **No request** (`receber`): confere tamanho e tipo, grava o arquivo e cria a
   linha com status `pendente`. Responde 202 na hora: ler um PDF de 30 páginas
   não pode segurar a tela do onboarding.
2. **Depois da resposta** (`processar`): abre o PDF, extrai o texto e marca
   `processada` ou `falhou`, com o motivo. Com o texto pronto, a IA lê as
   disciplinas e os assuntos e os liga ao catálogo (`services/assuntos_ementa.py`,
   #38), com status próprio (`status_assuntos`).

O arquivo vai para `diretorio_midia/ementas/<aluno>/`, fora de
`/media/avatares` — a única pasta servida publicamente. Ementa não tem URL.

A mesma ementa enviada de novo (pelo mesmo aluno ou por um colega do mesmo
curso) é reconhecida pelo SHA-256 e reaproveita o texto já extraído, sem passar
pelo PDF outra vez, e as disciplinas já lidas, sem chamar a IA.
"""

import asyncio
import hashlib
import logging
import shutil
import uuid
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.ia import ProvedorIA
from app.models import Ementa, StatusAssuntos, StatusEmenta, Usuario
from app.services import assuntos_ementa, ppc

logger = logging.getLogger(__name__)

# Todo PDF começa com isto, e a especificação aceita até 1 KB de lixo antes.
_ASSINATURA_PDF = b"%PDF-"

# Abaixo disto o PDF não tem texto de verdade: é uma ementa escaneada, que é
# imagem. A leitura por OCR é da #38.
MINIMO_DE_CARACTERES = 50


class EmentaInvalida(Exception):
    """O arquivo não é um PDF. A mensagem vai para o aluno."""


class EmentaGrandeDemais(Exception):
    """O arquivo passa de `tamanho_maximo_ementa`."""


def diretorio() -> Path:
    return Path(settings.diretorio_midia) / "ementas"


def receber(db: Session, usuario: Usuario, conteudo: bytes, nome_original: str | None) -> Ementa:
    """Grava o PDF e cria a ementa. Se já houver texto para este arquivo, ela já sai pronta."""
    if len(conteudo) > settings.tamanho_maximo_ementa:
        raise EmentaGrandeDemais
    if _ASSINATURA_PDF not in conteudo[:1024]:
        raise EmentaInvalida("Envie a ementa em PDF.")

    pasta = diretorio() / str(usuario.id)
    pasta.mkdir(parents=True, exist_ok=True)
    nome = f"{uuid.uuid4().hex}.pdf"
    (pasta / nome).write_bytes(conteudo)

    hash_sha256 = hashlib.sha256(conteudo).hexdigest()
    ementa = Ementa(
        usuario_id=usuario.id,
        curso_id=usuario.curso_id,
        periodo=usuario.periodo,
        arquivo_path=f"ementas/{usuario.id}/{nome}",
        # Só o nome, sem caminho: é o que o aluno reconhece, e o resto é do
        # computador dele.
        nome_original=Path(nome_original or "ementa.pdf").name[:255],
        tamanho_bytes=len(conteudo),
        hash_sha256=hash_sha256,
        status=StatusEmenta.pendente,
    )

    ja_lida = _ja_processada(db, hash_sha256)
    if ja_lida is not None:
        ementa.status = StatusEmenta.processada
        ementa.texto_extraido = ja_lida.texto_extraido
        ementa.paginas = ja_lida.paginas
        ementa.pagina_inicial = ja_lida.pagina_inicial
        ementa.pagina_final = ja_lida.pagina_final

    db.add(ementa)
    try:
        db.commit()
    except Exception:
        (pasta / nome).unlink(missing_ok=True)
        raise
    return ementa


def atual_do_aluno(db: Session, usuario: Usuario) -> Ementa | None:
    """A última ementa que o aluno enviou."""
    return db.scalars(
        select(Ementa)
        .where(Ementa.usuario_id == usuario.id)
        .order_by(Ementa.criado_em.desc(), Ementa.id.desc())
        .limit(1)
    ).first()


def obter_do_aluno(db: Session, usuario: Usuario, ementa_id: int) -> Ementa | None:
    """A ementa, se ela for deste aluno. A de outro responde como inexistente."""
    ementa = db.get(Ementa, ementa_id)
    return ementa if ementa is not None and ementa.usuario_id == usuario.id else None


def precisa_processar(ementa: Ementa) -> bool:
    """Falta extrair o texto ou ler os assuntos."""
    return ementa.status is StatusEmenta.pendente or (
        ementa.status is StatusEmenta.processada
        and ementa.status_assuntos is StatusAssuntos.pendente
    )


def reler_assuntos(db: Session, ementa: Ementa) -> bool:
    """Põe a leitura dos assuntos de volta na fila. `False` se ela não pode ser refeita agora.

    Serve para a IA que estava fora do ar e para o catálogo que cresceu desde
    a leitura. Só depois do texto extraído e fora de uma leitura em andamento.
    """
    if ementa.status is not StatusEmenta.processada:
        return False
    if ementa.status_assuntos is StatusAssuntos.processando:
        return False
    ementa.status_assuntos = StatusAssuntos.pendente
    ementa.erro_assuntos = None
    db.commit()
    return True


def processar(fabrica: sessionmaker[Session], provedor: ProvedorIA, ementa_id: int) -> None:
    """Extrai o texto da ementa e lê os assuntos. Roda depois da resposta, com sessão própria.

    Nunca levanta: um erro aqui não tem para quem subir (a resposta já foi), então
    ele vira `falhou` com o motivo, que é o que o aluno consulta.
    """
    with fabrica() as db:
        ementa = db.get(Ementa, ementa_id)
        if ementa is None:
            return
        if ementa.status is StatusEmenta.pendente:
            _extrair(db, ementa)
        if (
            ementa.status is StatusEmenta.processada
            and ementa.status_assuntos is StatusAssuntos.pendente
        ):
            # A tarefa em segundo plano roda numa thread, sem event loop.
            asyncio.run(assuntos_ementa.processar(db, provedor, ementa))


def _extrair(db: Session, ementa: Ementa) -> None:
    ementa.status = StatusEmenta.processando
    db.commit()

    try:
        extraido = _extrair_texto(Path(settings.diretorio_midia) / ementa.arquivo_path)
    except EmentaInvalida as erro:
        ementa.status = StatusEmenta.falhou
        ementa.erro = str(erro)
    except Exception:
        logger.exception("Falha inesperada ao ler a ementa %s", ementa.id)
        ementa.status = StatusEmenta.falhou
        ementa.erro = "Não foi possível ler o PDF. Tente enviar outro arquivo."
    else:
        ementa.status = StatusEmenta.processada
        ementa.texto_extraido = extraido.texto
        ementa.paginas = extraido.paginas
        # 1 a N, como o aluno vê no leitor de PDF.
        ementa.pagina_inicial = extraido.trecho.inicio + 1
        ementa.pagina_final = extraido.trecho.fim + 1
    db.commit()


def apagar_do_aluno(usuario_id: int) -> None:
    """Apaga os PDFs do aluno. Chamado pelo expurgo da conta."""
    shutil.rmtree(diretorio() / str(usuario_id), ignore_errors=True)


def _ja_processada(db: Session, hash_sha256: str) -> Ementa | None:
    return (
        db.execute(
            select(Ementa)
            .where(Ementa.hash_sha256 == hash_sha256, Ementa.status == StatusEmenta.processada)
            .limit(1)
        )
        .scalars()
        .first()
    )


@dataclass(frozen=True)
class _Extraido:
    texto: str
    paginas: int
    trecho: ppc.Trecho


def _extrair_texto(caminho: Path) -> _Extraido:
    """O texto do ementário do PDF e onde ele está.

    O aluno costuma mandar o PPC inteiro, de centenas de páginas: o texto
    guardado (e lido pela IA) é só o trecho com as ementas (`services/ppc.py`).
    Não há teto de páginas; o de bytes, conferido no upload, segura o tamanho.
    """
    try:
        leitor = PdfReader(BytesIO(caminho.read_bytes()))
        if leitor.is_encrypted and not leitor.decrypt(""):
            raise EmentaInvalida("O PDF está protegido por senha. Envie uma cópia sem senha.")
        paginas = [(pagina.extract_text() or "") for pagina in leitor.pages]
        trecho = ppc.localizar(paginas, _marcadores(leitor))
    except PyPdfError as erro:
        raise EmentaInvalida("O arquivo parece um PDF, mas está corrompido.") from erro

    texto = "\n".join(paginas[trecho.inicio : trecho.fim + 1]).strip()
    if len(texto) < MINIMO_DE_CARACTERES:
        raise EmentaInvalida(
            "Não encontramos texto no PDF. Se ele for uma ementa escaneada, envie a "
            "versão em texto; a leitura de documentos escaneados ainda não está disponível."
        )
    logger.info(
        "Ementário nas páginas %d a %d de %d (%s)",
        trecho.inicio + 1,
        trecho.fim + 1,
        len(paginas),
        trecho.metodo,
    )
    return _Extraido(texto, len(paginas), trecho)


def _marcadores(leitor: PdfReader) -> list[tuple[str, int]]:
    """Os itens do índice lateral do PDF, em ordem, com a página de cada um."""
    itens: list[tuple[str, int]] = []

    def percorrer(nivel: list) -> None:
        for item in nivel:
            if isinstance(item, list):
                percorrer(item)
                continue
            pagina = leitor.get_destination_page_number(item)
            if pagina is not None and pagina >= 0:
                itens.append((str(item.title or ""), pagina))

    try:
        percorrer(leitor.outline)
    except (PyPdfError, KeyError, TypeError):
        # Índice malformado não impede a leitura: o sumário e a densidade
        # ainda podem achar o ementário.
        return []
    return itens
