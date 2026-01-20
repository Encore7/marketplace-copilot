FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (for things like duckdb/pandas building wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only what we actually need for the app
COPY pyproject.toml ./
COPY backend ./backend
COPY config ./config
COPY data ./data
COPY eval ./eval
COPY prompts ./prompts

# Install dependencies + our package
RUN pip install --upgrade pip && pip install .

# Run as non-root
RUN useradd -m appuser
USER appuser

# Run the FastAPI app
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
