"""Foto do perfil (tela 18): validar, reprocessar e guardar fora do banco.

A imagem enviada **nunca** é gravada como chegou. Ela é aberta, recortada num
quadrado e salva de novo em WebP, e isso resolve três problemas de uma vez:

- o tipo é decidido pelo conteúdo, não pela extensão nem pelo `Content-Type`
  que o navegador declarou: um PDF renomeado para `.png` não abre como imagem;
- os metadados da original (o EXIF, que pode trazer a localização GPS de onde
  a foto foi tirada) ficam para trás, porque a imagem nova é gerada sem eles;
- um arquivo que é imagem e outra coisa ao mesmo tempo (poliglota) vira só
  imagem: o que sai é o que o Pillow desenhou, não os bytes do aluno.

O arquivo vai para `diretorio_midia/avatares` e é servido em `/media/avatares`.
Só essa pasta é pública: as ementas em PDF (#28), quando chegarem, ficam fora
dela.
"""

import secrets
import warnings
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Usuario

# Prefixo público de `avatar_url` para as fotos guardadas aqui. Avatar que não
# começa com ele veio do GitHub ou do Google e não é arquivo nosso.
PREFIXO_URL = "/media/avatares/"

FORMATOS_ACEITOS = {"PNG", "JPEG", "WEBP"}

# Lado do quadrado salvo. O maior uso é o cabeçalho do perfil, com 96 px; o
# dobro cobre tela de alta densidade.
LADO = 256

# Teto de pixels da imagem *aberta*. O limite de bytes não basta: um PNG de
# poucos KB pode descomprimir em gigabytes de memória.
MAXIMO_DE_PIXELS = 25_000_000


class AvatarInvalido(Exception):
    """O arquivo não é uma imagem aceita. A mensagem vai para o aluno."""


class AvatarGrandeDemais(Exception):
    """O arquivo passa de `tamanho_maximo_avatar`."""


def diretorio() -> Path:
    return Path(settings.diretorio_midia) / "avatares"


def salvar(db: Session, usuario: Usuario, conteudo: bytes) -> str:
    """Troca a foto do aluno. Devolve a `avatar_url` nova."""
    if len(conteudo) > settings.tamanho_maximo_avatar:
        raise AvatarGrandeDemais

    imagem = _reprocessar(conteudo)

    destino = diretorio()
    destino.mkdir(parents=True, exist_ok=True)
    # Nome novo a cada envio: a URL muda, e o navegador não mostra a foto velha
    # do cache.
    nome = f"{usuario.id}-{secrets.token_hex(8)}.webp"
    (destino / nome).write_bytes(imagem)

    anterior = usuario.avatar_url
    usuario.avatar_url = PREFIXO_URL + nome
    try:
        db.commit()
    except Exception:
        # O banco não aceitou: o arquivo novo ficaria órfão.
        apagar_arquivo(PREFIXO_URL + nome)
        raise

    # Só depois do commit: se ele falhasse, o aluno ficaria sem foto nenhuma.
    apagar_arquivo(anterior)
    return usuario.avatar_url


def remover(db: Session, usuario: Usuario) -> None:
    anterior = usuario.avatar_url
    usuario.avatar_url = None
    db.commit()
    apagar_arquivo(anterior)


def apagar_arquivo(avatar_url: str | None) -> None:
    """Apaga o arquivo da foto, se ela for nossa. Avatar externo não é tocado."""
    if not avatar_url or not avatar_url.startswith(PREFIXO_URL):
        return
    # `name` descarta qualquer pedaço de caminho: a URL vem do banco, mas não
    # custa garantir que nada fora da pasta seja apagado.
    (diretorio() / Path(avatar_url).name).unlink(missing_ok=True)


def _reprocessar(conteudo: bytes) -> bytes:
    try:
        with warnings.catch_warnings():
            # O Pillow só avisa entre 1x e 2x o limite dele; aqui o aviso já recusa.
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(conteudo)) as original:
                if original.format not in FORMATOS_ACEITOS:
                    raise AvatarInvalido("Envie uma imagem PNG, JPEG ou WebP.")
                if original.width * original.height > MAXIMO_DE_PIXELS:
                    raise AvatarInvalido("A imagem tem resolução grande demais.")

                # Foto de celular costuma vir deitada, com a rotação só no EXIF.
                # Aplica antes, porque o EXIF não vai junto para a imagem nova.
                imagem = ImageOps.exif_transpose(original)
                modo = "RGBA" if "A" in imagem.getbands() else "RGB"
                quadrado = ImageOps.fit(
                    imagem.convert(modo), (LADO, LADO), Image.Resampling.LANCZOS
                )
    except AvatarInvalido:
        raise
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        SyntaxError,
        ValueError,
    ) as erro:
        # Não é imagem, ou é imagem corrompida/truncada.
        raise AvatarInvalido("Envie uma imagem PNG, JPEG ou WebP.") from erro

    saida = BytesIO()
    quadrado.save(saida, format="WEBP", quality=85)
    return saida.getvalue()
