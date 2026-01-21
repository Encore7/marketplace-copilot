from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.endpoints.analyze import router as analyze_router
from backend.app.api.endpoints.health import router as health_router
from backend.app.api.endpoints.root import router as root_router

router = APIRouter()
router.include_router(root_router)
router.include_router(health_router)
router.include_router(analyze_router)
