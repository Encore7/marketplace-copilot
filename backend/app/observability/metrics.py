from __future__ import annotations

import time
from typing import Awaitable, Callable

from fastapi import APIRouter, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

REQUEST_COUNTER = Counter(
    "copilot_http_requests_total",
    "Total HTTP requests handled by the API",
    ["method", "path", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "copilot_http_request_latency_seconds",
    "Latency of HTTP requests in seconds",
    ["method", "path"],
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware that tracks basic HTTP metrics.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        latency = time.perf_counter() - start

        path = request.url.path

        if path != "/metrics":
            REQUEST_COUNTER.labels(
                method=request.method,
                path=path,
                status_code=response.status_code,
            ).inc()

            REQUEST_LATENCY.labels(
                method=request.method,
                path=path,
            ).observe(latency)

        return response


metrics_router = APIRouter(tags=["metrics"])


@metrics_router.get("/metrics")
async def metrics() -> Response:
    """
    Prometheus metrics endpoint.
    """
    data: bytes = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
