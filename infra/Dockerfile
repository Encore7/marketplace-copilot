FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Minimal system deps (duckdb/pandas etc. may need these)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only what's needed to build & run the API
COPY pyproject.toml ./pyproject.toml
COPY backend ./backend

# Install project (and its deps) as a package
RUN pip install --upgrade pip \
    && pip install .

# Run as non-root
RUN useradd -m appuser
USER appuser

# Ensure backend is importable
ENV PYTHONPATH=/app

# Entrypoint: production uvicorn
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
