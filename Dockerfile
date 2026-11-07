# CPU-only runtime for the original Jon2 FastAPI service.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/ai_engine \
    JON2_CHECKPOINT=/app/model-weights/jon2-small.pt

WORKDIR /app

RUN pip install --no-cache-dir fastapi "uvicorn[standard]" kaggle && \
    pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch

COPY ai_engine/ /app/ai_engine/
COPY index.html /app/index.html
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh && mkdir -p /app/model-weights

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8000') + '/api/health/live', timeout=4).read()"

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["sh", "-c", "uvicorn main:app --app-dir /app/ai_engine --host 0.0.0.0 --port ${PORT:-8000}"]
