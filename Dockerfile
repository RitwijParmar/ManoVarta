FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

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

EXPOSE 8000

CMD ["sh", "-c", "uvicorn manovarta_core.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
