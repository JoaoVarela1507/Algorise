FROM python:3.13-slim AS base

# Preenchidos pelo CI; em build local ficam como "unknown" (ver issue #42).
ARG GIT_COMMIT=unknown
ARG BUILD_TIME
ENV GIT_COMMIT=${GIT_COMMIT} \
    BUILD_TIME=${BUILD_TIME} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copiar só o requirements primeiro aproveita o cache do Docker: mudar código
# não reinstala as dependências.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

# A API não precisa de root para servir HTTP. A pasta das fotos do perfil nasce
# aqui para o volume do compose herdar o dono e o usuário sem root poder gravar.
RUN mkdir -p /app/media/avatares     && useradd --create-home --uid 1000 algorise && chown -R algorise:algorise /app
USER algorise

# Worker da fila (#206): o mesmo código, mais o que a transcrição dos vídeos
# (#208) usa. Fica antes da API para ela continuar sendo o estágio padrão de um
# `docker build` sem `--target`, que é o que a CI constrói.
FROM base AS worker
USER root
# A sandbox do desafio de código (#34) sobe um container por caso de teste: o
# worker precisa do cliente do Docker. Só o binário, sem o daemon.
COPY --from=docker:27-cli /usr/local/bin/docker /usr/local/bin/docker
COPY requirements-transcricao.txt .
RUN pip install --no-cache-dir -r requirements-transcricao.txt \
    && mkdir -p /app/modelos && chown algorise:algorise /app/modelos
USER algorise
# O modelo do Whisper é baixado uma vez, para o volume montado aqui.
ENV HF_HOME=/app/modelos
# O worker não serve HTTP: não há `/health` para conferir.
HEALTHCHECK NONE
CMD ["rq", "worker", "algorise", "--with-scheduler"]

FROM base AS api

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
