from __future__ import annotations

from ..observability.logging import get_logger
from .state import HITLFeedback, SellerState

logger = get_logger("agents.hitl")


def initialize_hitl_feedback(state: SellerState) -> SellerState:
    """
    HITL Feedback Agent (skeleton).

    Responsibilities:
      - Ensure that a HITL feedback container exists in the state.
      - This allows downstream API endpoints to attach user feedback
        about the quality/usefulness of the copilot's response.

    Real feedback ingestion will likely come from a separate endpoint that
    accepts a conversation_id / request_id and a rating/comment, then maps
    it into this structure for training/evals.
    """
    if state.hitl_feedback is None:
        state.hitl_feedback = HITLFeedback(
            rating=None,
            comment=None,
            metadata={},
        )
        logger.info("HITL feedback structure initialized in state")
    else:
        logger.info("HITL feedback already present in state")

    return state
