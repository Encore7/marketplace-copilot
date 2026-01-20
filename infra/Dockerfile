FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject
COPY pyproject.toml ./

# Install app + dependencies
RUN pip install --upgrade pip && pip install .

# Copy application code
COPY backend ./backend
COPY config ./config
COPY data ./data
COPY eval ./eval
COPY prompts ./prompts

# Non-root user
RUN useradd -m appuser
USER appuser

ENV PYTHONPATH=/app

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
