from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.router import router as api_router
from .core.config import settings
from .db.chat_store import init_chat_store
from .observability import otel
from .observability.logging import setup_logging
from .observability.metrics import MetricsMiddleware, metrics_router
from .observability.middleware import TraceLoggingMiddleware


def create_app() -> FastAPI:
    """
    Application factory.

    - Sets up JSON logging with trace/span IDs
    - Configures OpenTelemetry tracing
    - Attaches HTTP middlewares (CORS, tracing logs, metrics)
    - Registers versioned API routes and metrics endpoint
    """
    # Configure logging
    setup_logging()
    init_chat_store()

    app = FastAPI(
        title=settings.app.name,
        version="0.1.0",
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    # Observability: tracing via OTLP to Alloy -> Tempo
    otel.init_otel(app)

    # Middlewares
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(TraceLoggingMiddleware)
    app.add_middleware(MetricsMiddleware)

    # Versioned API router
    app.include_router(api_router, prefix="/api/v1")

    # Metrics endpoint (root-level /metrics)
    app.include_router(metrics_router)

    return app


app = create_app()
