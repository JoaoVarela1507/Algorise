from pydantic import BaseModel

__all__ = ["EntradaRanking", "Ranking"]


class EntradaRanking(BaseModel):
    """Uma linha do pódio ou da lista rolável (telas 16 e 17)."""

    posicao: int
    usuario_id: int
    username: str
    nome_exibicao: str
    avatar_url: str | None = None
    xp: int


class Ranking(BaseModel):
    podio: list[EntradaRanking]
    lista: list[EntradaRanking]
    total: int
    # Onde o aluno esta. Fica fora da lista porque a tela 16 mostra a posicao
    # dele mesmo quando ela cai na pagina 40.
    usuario: EntradaRanking | None = None
