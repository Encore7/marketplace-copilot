from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/",
    tags=["root"],
    summary="API root – basic sanity check",
)
async def root() -> dict:
    """
    Basic root endpoint for API v1.
    Useful for smoke tests and quick verification that the service is up.
    """
    return {
        "message": "Marketplace Seller Intelligence Copilot API skeleton",
        "version": "v1",
    }
