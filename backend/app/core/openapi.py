"""Ajustes do OpenAPI: `operation_id`, tags e respostas de erro.

O `/openapi.json` não é só documentação: é dele que saem os tipos TypeScript do
frontend (`npm run gen:api`). Duas consequências práticas:

- o `operation_id` vira nome de função no cliente gerado, então ele precisa ser
  legível e **estável**. O padrão do FastAPI inclui rota e método
  (`listar_trilhas_api_v1_trilhas_get`), o que muda o nome do cliente inteiro
  quando a rota muda de lugar. Aqui ele sai do nome da função e só muda quando
  alguém renomeia a função;
- o formato de erro precisa estar documentado, senão o cliente gerado não sabe
  o que vem num 4xx.
"""

from typing import Any

from fastapi.routing import APIRoute

from app.core.erros import RespostaDeErro

# Descrição das tags, que o /docs mostra como cabeçalho de cada grupo.
TAGS = [
    {"name": "auth", "description": "Cadastro, login, sessão e recuperação de senha."},
    {"name": "usuarios", "description": "O aluno logado sobre a própria conta."},
    {"name": "trilhas", "description": "Catálogo de trilhas, módulos e atividades."},
    {"name": "ranking", "description": "Pódio e classificação por XP."},
    {"name": "health", "description": "Vivo e pronto para servir. Fora do contrato versionado."},
    {"name": "version", "description": "Versão, commit e ambiente da API."},
]

# Entram em toda rota: qualquer uma pode devolver 422 (validação) e 500.
RESPOSTAS_PADRAO: dict[int | str, dict[str, Any]] = {
    422: {"model": RespostaDeErro, "description": "Dados inválidos"},
    500: {"model": RespostaDeErro, "description": "Erro inesperado"},
}


def gerar_operation_id(rota: APIRoute) -> str:
    """`listar_trilhas` -> `listarTrilhas`.

    camelCase porque o consumidor é TypeScript. Rotas com o mesmo nome de função
    em arquivos diferentes precisam ser renomeadas — o OpenAPI exige id único, e
    o FastAPI avisa no boot se houver repetição.
    """
    partes = rota.name.split("_")
    return partes[0] + "".join(parte.title() for parte in partes[1:])
