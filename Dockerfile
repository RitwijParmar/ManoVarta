FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    MANOVARTA_SELF_HOSTED_MODEL_DIR=/models/qwen2.5-0.5b-instruct \
    HF_HUB_DISABLE_TELEMETRY=1

WORKDIR /app

COPY pyproject.toml README.md manage.py .env.example ./
COPY manovarta_core ./manovarta_core
COPY manovarta_admin ./manovarta_admin
COPY screening ./screening
COPY training ./training
COPY data ./data

RUN pip install --upgrade pip \
    && pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.2" \
    && pip install ".[runtime-cloud]"

RUN python -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen2.5-0.5B-Instruct', local_dir='/models/qwen2.5-0.5b-instruct', ignore_patterns=['*.onnx', '*.h5', '*.msgpack', 'original/*'])"

EXPOSE 8000

CMD ["sh", "-c", "uvicorn manovarta_core.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
