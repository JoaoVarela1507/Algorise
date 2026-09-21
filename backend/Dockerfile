FROM python:3.13-slim

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

# A API não precisa de root para servir HTTP.
RUN useradd --create-home --uid 1000 algorise && chown -R algorise:algorise /app
USER algorise

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
