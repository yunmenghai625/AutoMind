FROM public.ecr.aws/docker/library/python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY apps/__init__.py ./apps/__init__.py
COPY apps/api ./apps/api
COPY data/knowledge ./data/knowledge
COPY alembic.ini ./
COPY migrations ./migrations

RUN python -m pip install --no-cache-dir --upgrade "pip>=26.2" \
    && pip install --no-cache-dir . \
    && addgroup --system automind \
    && adduser --system --ingroup automind automind \
    && mkdir -p /app/data/generated \
    && chown -R automind:automind /app/data

USER automind

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:' + __import__('os').environ.get('PORT', '8000') + '/health', timeout=3)" || exit 1

CMD ["sh", "-c", "alembic upgrade head && python -m apps.api.rag.ingest_cli data/knowledge && exec uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
