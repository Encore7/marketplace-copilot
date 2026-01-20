from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@router.get(
    "",
    summary="Service health check",
)
async def health_check() -> dict:
    """
    Lightweight liveness probe endpoint.
    Can be used by Docker healthcheck, or monitoring.
    """
    return {"status": "ok"}
