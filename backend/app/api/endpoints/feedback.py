from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

from ...observability.logging import get_logger

logger = get_logger("api.feedback")

router = APIRouter(tags=["feedback"])


class FeedbackRequest(BaseModel):
    """
    Payload for user feedback on a copilot response.

    In a real system this would be tied to:
      - a conversation_id / request_id
      - user_id / seller_id
      - possibly the full state snapshot in a warehouse

    For now we just log it with trace/span IDs and return 202 Accepted.
    """

    model_config = ConfigDict(extra="ignore")

    request_id: str = Field(
        ...,
        description="Identifier of the analyze request / conversation this feedback refers to.",
    )
    rating: Optional[int] = Field(
        default=None,
        ge=1,
        le=5,
        description="Optional 1–5 rating for the copilot response quality.",
    )
    comment: Optional[str] = Field(
        default=None,
        description="Optional free-text comment from the user.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional structured metadata (UI context, experiment flags, etc.).",
    )


class FeedbackResponse(BaseModel):
    status: str = Field(
        ...,
        description="Status of feedback ingestion (e.g. 'accepted').",
    )


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    summary="Submit human feedback on a copilot response.",
)
async def submit_feedback(payload: FeedbackRequest) -> FeedbackResponse:
    """
    Simple feedback ingestion endpoint.

    For now:
      - Logs the feedback as a structured JSON log line with trace/span IDs.
      - Returns a generic 'accepted' status.

    Later:
      - This can push feedback into a real warehouse / queue (e.g., Kafka, Postgres).
    """
    logger.info(
        "Feedback received",
        extra={
            "request_id": payload.request_id,
            "rating": payload.rating,
            "has_comment": bool(payload.comment),
            "metadata": payload.metadata,
        },
    )

    return FeedbackResponse(status="accepted")
