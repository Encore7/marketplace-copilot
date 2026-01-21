from __future__ import annotations

import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("request")


class TraceLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs each request with trace_id/span_id injected by the logging factory.
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        logger.info(
            "Incoming request",
            extra={"path": request.url.path, "method": request.method},
        )
        response = await call_next(request)
        logger.info(
            "Completed request",
            extra={
                "path": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
            },
        )
        return response
