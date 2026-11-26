# CPU-only runtime for the original Jon2 FastAPI service.
# Health-only by default: no checkpoint or external model is bundled.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/ai_engine \
    JON2_CHECKPOINT=/app/model-weights/jon2-small.pt \
    JON2_CHAT_RELEASE_APPROVED=false \
    JON2_INFERENCE_TESTED=false \
    JON2_QUALITY_REVIEW_PASSED=false \
    JON2_PRELOAD_MODEL=false

WORKDIR /app

RUN pip install --no-cache-dir fastapi "uvicorn[standard]" && \
    pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch

COPY ai_engine/ /app/ai_engine/
COPY index.html /app/index.html

RUN rm -rf /app/ai_engine/checkpoints /app/ai_engine/training_data /app/ai_engine/evaluation && \
    mkdir -p /app/model-weights

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8000') + '/api/health/live', timeout=4).read()"

CMD ["sh", "-c", "uvicorn main:app --app-dir /app/ai_engine --host 0.0.0.0 --port ${PORT:-8000}"]
