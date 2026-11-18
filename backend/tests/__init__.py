"""Suite de testes do backend."""

import os

# A sandbox e o provedor de IA dos testes são os padrões (como no CI, que não
# tem `.env`), e não os do `.env` de quem roda: com `SANDBOX_MODO=processo` ou
# `IA_PROVEDOR=gemini` no `.env` local, os testes que montam `Settings` de
# produção ou conferem o padrão falhariam só nesta máquina. A variável de
# ambiente vale mais que o `.env`, e este arquivo roda antes do `conftest`.
os.environ["SANDBOX_MODO"] = "docker"
os.environ["IA_PROVEDOR"] = "ollama"
os.environ["IA_RESERVA"] = ""
os.environ["IA_PROVEDOR_EMBEDDINGS"] = ""
os.environ["GEMINI_MODELOS"] = ""
os.environ["OLLAMA_MANTER_CARREGADO"] = ""
