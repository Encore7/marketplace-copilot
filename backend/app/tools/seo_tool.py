from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from ..observability.logging import get_logger

logger = get_logger("tools.seo")


class SEOEvaluationInput(BaseModel):
    product_id: str
    marketplace: str
    title: str
    bullets: List[str] = Field(default_factory=list)
    description: str = ""


class SEOSuggestion(BaseModel):
    field: str
    suggestion: str
    rationale: str


class SEOEvaluationOutput(BaseModel):
    product_id: str
    marketplace: str
    score: float
    issues: List[str]
    suggestions: List[SEOSuggestion]


def evaluate_seo(input_data: SEOEvaluationInput) -> SEOEvaluationOutput:
    """
    Tool: basic heuristic SEO evaluation for a listing.

    Heuristics:
      - Title length (not too short, not too long)
      - Presence of bullets
      - Description length
    """
    issues: List[str] = []
    suggestions: List[SEOSuggestion] = []

    title_len = len(input_data.title)
    desc_len = len(input_data.description)
    num_bullets = len(input_data.bullets)

    score = 100.0

    # Title checks
    if title_len < 30:
        score -= 10
        issues.append("Title is too short.")
        suggestions.append(
            SEOSuggestion(
                field="title",
                suggestion="Add more descriptive keywords to the title.",
                rationale="Short titles often miss important search terms.",
            )
        )
    elif title_len > 150:
        score -= 10
        issues.append("Title may be too long.")
        suggestions.append(
            SEOSuggestion(
                field="title",
                suggestion="Shorten the title while keeping key phrases.",
                rationale="Very long titles can be truncated and may reduce clarity.",
            )
        )

    # Bullets
    if num_bullets < 3:
        score -= 10
        issues.append("Too few bullet points for features/benefits.")
        suggestions.append(
            SEOSuggestion(
                field="bullets",
                suggestion="Add at least 3–5 bullet points covering key features and benefits.",
                rationale="Bullet points help buyers quickly scan product advantages.",
            )
        )

    # Description
    if desc_len < 100:
        score -= 10
        issues.append("Description is very short.")
        suggestions.append(
            SEOSuggestion(
                field="description",
                suggestion="Expand the description to cover use cases, materials, sizing, and care.",
                rationale="Richer descriptions can improve conversion and reduce returns.",
            )
        )

    score = max(0.0, min(score, 100.0))

    return SEOEvaluationOutput(
        product_id=input_data.product_id,
        marketplace=input_data.marketplace,
        score=score,
        issues=issues,
        suggestions=suggestions,
    )
