# CPU-only runtime for the original Jon2 FastAPI service.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/ai_engine

WORKDIR /app

# Install the CPU wheel explicitly to avoid downloading CUDA packages.
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" && \
    pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch

COPY ai_engine/ /app/ai_engine/

EXPOSE 8000

# Liveness checks only whether the API process responds; model readiness is separate.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8000') + '/api/health/live', timeout=4).read()"

CMD ["sh", "-c", "uvicorn main:app --app-dir /app/ai_engine --host 0.0.0.0 --port ${PORT:-8000}"]
