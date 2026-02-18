from __future__ import annotations

from fastapi import APIRouter

from .endpoints.analyze import router as analyze_router
from .endpoints.chat import router as chat_router
from .endpoints.debug import router as debug_router
from .endpoints.feedback import router as feedback_router  # NEW
from .endpoints.health import router as health_router
from .endpoints.root import router as root_router

router = APIRouter()

router.include_router(root_router)
router.include_router(health_router)
router.include_router(analyze_router)
router.include_router(chat_router)
router.include_router(feedback_router)  # NEW
router.include_router(debug_router)
