# CPU-only runtime for the project-owned Jon2 FastAPI service.
# Private model weights are deliberately NOT copied into this image or Git.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/ai_engine \
    JON2_CHECKPOINT=/app/model-weights/jon2-last.pt \
    JON2_CHECKPOINT_SHA256=edf96971187f93642f36282e270c2d2f3a6db39565b30d7898e856a49e0eaec2 \
    JON2_PRELOAD_MODEL=true \
    JON2_CHAT_RELEASE_APPROVED=false \
    JON2_INFERENCE_TESTED=false \
    JON2_QUALITY_REVIEW_PASSED=false

WORKDIR /app

RUN pip install --no-cache-dir fastapi "uvicorn[standard]" httpx && \
    pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch

COPY ai_engine/ /app/ai_engine/
COPY index.html /app/index.html
COPY jon2-config.js /app/jon2-config.js
COPY assets/ /app/assets/
COPY manifest.webmanifest /app/manifest.webmanifest
COPY service-worker.js /app/service-worker.js
COPY pocket/ /app/pocket/
COPY docker-entrypoint.sh /app/docker-entrypoint.sh

RUN chmod +x /app/docker-entrypoint.sh && mkdir -p /app/model-weights

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8000') + '/api/health/live', timeout=4).read()"

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["sh", "-c", "uvicorn main:app --app-dir /app/ai_engine --host 0.0.0.0 --port ${PORT:-8000}"]
