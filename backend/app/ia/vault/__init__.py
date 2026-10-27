"""Vault das skills de IA (#200): base de conhecimento consultada como um RAG.

- `trechos`: lê as transcrições (.srt, .vtt, .txt) e divide o texto em trechos;
- `ingestao`: grava transcrições, módulos do catálogo e prompts com embedding,
  sem duplicar;
- `busca`: os trechos mais próximos de um texto, com filtro por trilha e
  disciplina. É por aqui, e só por aqui, que as skills consultam o vault.

Diferente das skills, o vault fala com o banco. Quem junta os trechos para uma
skill é o serviço que a usa, e a skill continua recebendo só texto.

Pela linha de comando, da pasta `backend/`:

    python -m app.ia.vault ingerir --modulo 3 aula.vtt
    python -m app.ia.vault registrar-modulos
    python -m app.ia.vault registrar-prompts

O `registrar-modulos` também roda sozinho antes de cada leitura de ementa
(#38), então só é preciso chamá-lo à mão para conferir o vault.
"""

from app.ia.vault.busca import Resultado, buscar, buscar_por_vetor
from app.ia.vault.ingestao import (
    Ingestao,
    ModuloNaoEncontrado,
    ingerir_transcricao,
    registrar_modulos,
    registrar_prompts,
)

__all__ = [
    "Ingestao",
    "ModuloNaoEncontrado",
    "Resultado",
    "buscar",
    "buscar_por_vetor",
    "ingerir_transcricao",
    "registrar_modulos",
    "registrar_prompts",
]
