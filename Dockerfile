FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    MANOVARTA_MODEL_PROVIDER=vertex \
    MANOVARTA_CHAT_PROVIDER=vertex \
    MANOVARTA_EXTRACTION_PROVIDER=vertex \
    MANOVARTA_SAFETY_PROVIDER=local \
    MANOVARTA_CHAT_MODEL=gemini-2.5-flash \
    MANOVARTA_EXTRACTION_MODEL=gemini-2.5-flash \
    MANOVARTA_VERTEX_LOCATION=us-central1 \
    MANOVARTA_LIVE_CHAT_LLM_ANALYSIS=true \
    MANOVARTA_LIVE_LLM_TURN_THRESHOLD=1 \
    MANOVARTA_ASYNC_SCORING_ENABLED=true \
    MANOVARTA_ASYNC_SCORING_DIR=/app/artifacts/async_scoring \
    MANOVARTA_LOCAL_SAFETY_CHECKPOINT= \
    HF_HUB_DISABLE_TELEMETRY=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY manovarta_core ./manovarta_core
COPY training ./training
COPY data/seed ./data/seed

RUN pip install --upgrade pip \
    && pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.2" \
    && pip install ".[runtime-cloud]"

EXPOSE 8000

CMD ["sh", "-c", "uvicorn manovarta_core.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
