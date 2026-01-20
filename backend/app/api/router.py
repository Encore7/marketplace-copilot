from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.endpoints import health, root

router = APIRouter()

# Core/root endpoints
router.include_router(root.router)

# Health/liveness endpoints
router.include_router(health.router)
