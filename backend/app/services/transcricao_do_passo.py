"""A transcrição do vídeo de um passo, para ler junto do player (#21, acessibilidade).

Vem do vault (#200), que já guarda as transcrições com o tempo de cada trecho:
- a do módulo, ingerida pela linha de comando (`documento.modulo_id`);
- a do vídeo do YouTube de que o módulo é uma parte (#208/#209), recortada no
  intervalo do módulo (`inicio_segundos` a `fim_segundos`).

Os trechos do vault se sobrepõem de propósito (o fim de um repete no começo do
seguinte, para a busca não perder a frase do corte). Para ler, a sobreposição
sai: senão a transcrição repetiria um pedaço a cada parágrafo.
"""

from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import DocumentoVault, Modulo, OrigemVault, TrechoVault

# Maior sobreposição procurada entre dois trechos, em palavras.
_SOBREPOSICAO_MAXIMA = 80


@dataclass(frozen=True)
class Fala:
    inicio: float | None
    fim: float | None
    texto: str


def falas_do_passo(db: Session, modulo: Modulo) -> list[Fala]:
    """As falas do vídeo do passo, na ordem. Vazio quando não há transcrição."""
    condicoes = [DocumentoVault.modulo_id == modulo.id]
    if modulo.parte_video is not None:
        condicoes.append(DocumentoVault.video_id == modulo.parte_video.video_id)
    documento = db.scalars(
        select(DocumentoVault)
        .where(DocumentoVault.origem == OrigemVault.transcricao, or_(*condicoes))
        # A do próprio módulo primeiro: foi ingerida para ele.
        .order_by(DocumentoVault.modulo_id.is_(None), DocumentoVault.id)
        .options(selectinload(DocumentoVault.trechos))
        .limit(1)
    ).first()
    if documento is None:
        return []

    trechos: list[TrechoVault] = list(documento.trechos)
    if documento.modulo_id is None and modulo.inicio_segundos is not None:
        trechos = [t for t in trechos if _dentro(t, modulo.inicio_segundos, modulo.fim_segundos)]

    falas: list[Fala] = []
    anterior = ""
    for trecho in trechos:
        texto = _sem_sobreposicao(anterior, trecho.texto)
        anterior = trecho.texto
        if texto:
            falas.append(Fala(trecho.inicio_segundos, trecho.fim_segundos, texto))
    return falas


def _dentro(trecho: TrechoVault, inicio: float, fim: float | None) -> bool:
    if trecho.inicio_segundos is None:
        return True
    comeco_ok = (trecho.fim_segundos or trecho.inicio_segundos) >= inicio
    return comeco_ok and (fim is None or trecho.inicio_segundos <= fim)


def _sem_sobreposicao(anterior: str, atual: str) -> str:
    """Tira do começo de `atual` o pedaço que repete o fim de `anterior`."""
    if not anterior:
        return atual.strip()
    fim_anterior = anterior.split()
    palavras = atual.split()
    limite = min(len(fim_anterior), len(palavras), _SOBREPOSICAO_MAXIMA)
    for tamanho in range(limite, 0, -1):
        if fim_anterior[-tamanho:] == palavras[:tamanho]:
            return " ".join(palavras[tamanho:])
    return " ".join(palavras)
