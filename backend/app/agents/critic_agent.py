# backend/app/agents/critic_agent.py
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from ..core.llm import LLMError, get_llm_client
from ..core.prompt import load_prompt
from ..observability.llm_obs import traceable_node
from ..observability.logging import get_logger
from .state import Critique, SellerState

logger = get_logger("agents.critic")


class CriticLLMOutput(BaseModel):
    """
    Expected JSON output for the critic.

    The critic does not change the action plan directly; it only provides
    meta feedback and optionally flags missing areas.
    """

    overall_comment: str = Field(
        ...,
        description="High-level critique of the action plan quality.",
    )
    strengths: List[str] = Field(
        default_factory=list,
        description="What the plan does well.",
    )
    weaknesses: List[str] = Field(
        default_factory=list,
        description="Gaps or issues in the plan.",
    )
    missing_areas: List[str] = Field(
        default_factory=list,
        description="Important business areas that are not covered.",
    )


def _build_critic_context(state: SellerState) -> str:
    lines: List[str] = []

    if state.query:
        lines.append("## User Query")
        lines.append(state.query.raw_query)
        lines.append("")

    if state.action_plan:
        lines.append("## Action Plan")
        lines.append(state.action_plan.overall_summary)
        lines.append("")
        lines.append("### Actions")
        for idx, action in enumerate(state.action_plan.actions, start=1):
            lines.append(
                f"{idx}. [{action.category.value}] {action.title} "
                f"(priority={action.priority.value}, impact={action.estimated_impact or 'n/a'})"
            )
        lines.append("")

    return "\n".join(lines)


@traceable_node("critic_agent")
def _call_critic_llm(prompt: str) -> CriticLLMOutput:
    client = get_llm_client()
    return client.generate_structured(prompt, CriticLLMOutput)


def update_critique(state: SellerState) -> SellerState:
    """
    Reflection / Critic Agent.

    Responsibilities:
      - Evaluate the quality of the current action plan.
      - Highlight strengths, weaknesses, and missing areas.
      - Store the results under state.critique.
    """
    critic_prompt_template = load_prompt("critic")  # prompts/critic_v1.md

    context_text = _build_critic_context(state)
    complete_prompt = (
        critic_prompt_template
        + "\n\n"
        + "-----\n\n"
        + "## Structured Context for Critic\n\n"
        + context_text
    )

    logger.info("Critic agent invoking LLM")

    try:
        llm_output = _call_critic_llm(complete_prompt)
    except LLMError as exc:
        logger.error(
            "Critic LLM call failed; leaving state.critique unchanged",
            extra={"error": str(exc)},
        )
        return state

    state.critique = Critique(
        comments=llm_output.overall_comment,
        detected_risks=llm_output.weaknesses,
        missing_elements=llm_output.missing_areas,
        score=None,
    )

    logger.info(
        "Critic agent updated critique",
        extra={
            "num_strengths": len(llm_output.strengths),
            "num_weaknesses": len(llm_output.weaknesses),
        },
    )

    return state
