from __future__ import annotations

from uuid import uuid4
from typing import List, Optional

from pydantic import BaseModel, Field

from ..core.llm import LLMError, get_llm_client
from ..core.prompt import load_prompt
from ..observability.llm_obs import traceable_node
from ..observability.logging import get_logger
from .state import (
    ActionCategory,
    ActionItem,
    ActionPlan,
    ActionPriority,
    FinalAnswer,
    SellerState,
)

logger = get_logger("agents.final_answer")


class FinalAnswerLLMAction(BaseModel):
    area: str = "general"
    title: str
    description: str
    priority: str = "medium"
    impact: str = "medium"
    product_id: str | None = None


class FinalAnswerLLMActionPlan(BaseModel):
    overall_summary: str = ""
    actions: List[FinalAnswerLLMAction] = Field(default_factory=list)


class FinalAnswerLLMOutput(BaseModel):
    """
    Expected JSON output from the final answer LLM.

    We allow the LLM to optionally refine the structured ActionPlan and
    provide a list of human-readable citation identifiers (e.g. doc/section).
    """

    answer_markdown: str = Field(
        ...,
        description="High-quality markdown answer for the seller.",
    )
    refined_action_plan: Optional[FinalAnswerLLMActionPlan] = Field(
        default=None,
        description="Optionally refined action plan; if absent, keep existing one.",
    )
    citations: List[str] = Field(
        default_factory=list,
        description=(
            "List of human-readable citation identifiers, e.g. "
            "`amazon:image_requirements:image_requirements.md#hero-image`."
        ),
    )


def _to_action_category(value: str) -> ActionCategory:
    normalized = (value or "").strip().lower()
    mapping = {
        "pricing": ActionCategory.PRICING,
        "listing": ActionCategory.LISTING,
        "seo": ActionCategory.SEO,
        "inventory": ActionCategory.INVENTORY,
        "compliance": ActionCategory.COMPLIANCE,
        "profitability": ActionCategory.PROFITABILITY,
    }
    return mapping.get(normalized, ActionCategory.OTHER)


def _to_action_priority(value: str) -> ActionPriority:
    normalized = (value or "").strip().lower()
    if normalized == "low":
        return ActionPriority.LOW
    if normalized == "high":
        return ActionPriority.HIGH
    if normalized == "critical":
        return ActionPriority.CRITICAL
    return ActionPriority.MEDIUM


def _normalize_action_plan(llm_plan: FinalAnswerLLMActionPlan) -> ActionPlan:
    actions: List[ActionItem] = []
    for action in llm_plan.actions:
        actions.append(
            ActionItem(
                id=f"final-{uuid4().hex[:8]}",
                product_id=action.product_id,
                title=action.title,
                description=action.description,
                category=_to_action_category(action.area),
                priority=_to_action_priority(action.priority),
                estimated_impact=action.impact,
            )
        )
    return ActionPlan(overall_summary=llm_plan.overall_summary, actions=actions)


def _build_citation_seeds(state: SellerState) -> List[str]:
    """
    Build a small list of default citation identifiers from RAGContext.

    The LLM can use these as hints or override them with more specific ones.
    """
    if not state.rag_context or not state.rag_context.chunks:
        return []

    seeds: List[str] = []

    for chunk in state.rag_context.chunks[:5]:
        marketplace = chunk.marketplace or "any"
        section = chunk.section or "unknown_section"
        source = chunk.source or "unknown_source"
        seeds.append(f"{marketplace}:{section}:{source}")

    return seeds


def _build_final_context(state: SellerState) -> str:
    """
    Build a text context summarizing the current SellerState for the final answer.

    This is more compact than the planner context but still gives the LLM
    enough signal to explain *why* recommendations were made.
    """
    lines: List[str] = []

    # Query
    if state.query:
        lines.append("## User Query")
        lines.append(state.query.raw_query)
        lines.append("")
        if state.query.seller_name:
            lines.append(f"- Seller name: {state.query.seller_name}")
        if state.query.session_id:
            lines.append(f"- Session ID: {state.query.session_id}")
        if state.query.memory_facts:
            lines.append("## Memory Facts")
            for fact in state.query.memory_facts:
                lines.append(f"- {fact}")
            lines.append("")
        if state.query.recent_chat_turns:
            lines.append("## Recent Conversation")
            for turn in state.query.recent_chat_turns:
                lines.append(f"- {turn}")
            lines.append("")

    # Action plan
    if state.action_plan:
        lines.append("## Action Plan (Structured)")
        lines.append(f"Overall summary: {state.action_plan.overall_summary}")
        if state.action_plan.actions:
            lines.append("")
            lines.append("Key actions:")
            for idx, action in enumerate(state.action_plan.actions[:10], start=1):
                lines.append(
                    f"{idx}. [{action.category.value}] {action.title} "
                    f"(priority={action.priority.value}, impact={action.estimated_impact or 'n/a'})"
                )
        lines.append("")

    # Sales
    if state.sales_analyses:
        lines.append("## Sales Highlights (up to 3 products)")
        for a in state.sales_analyses[:3]:
            lines.append(
                f"- Product {a.product_id}: units={a.total_units_sold}, "
                f"revenue={a.total_gross_revenue:.2f}, "
                f"returns={a.total_returns}, "
                f"CR={a.conversion_rate if a.conversion_rate is not None else 'n/a'}"
            )
        lines.append("")

    # Competitor
    if state.competitor_analyses:
        lines.append("## Competitor Highlights (up to 3 products)")
        for c in state.competitor_analyses[:3]:
            lines.append(
                f"- Product {c.product_id}: competitors={c.num_competitors}, "
                f"seller_avg_price={c.seller_avg_price}, "
                f"avg_comp_price={c.avg_competitor_price}"
            )
        lines.append("")

    # Inventory
    if state.inventory_analyses:
        lines.append("## Inventory & Risk (up to 3 products)")
        for inv in state.inventory_analyses[:3]:
            lines.append(
                f"- Product {inv.product_id}: stock={inv.current_stock}, "
                f"reorder_level={inv.reorder_level}, "
                f"risk={inv.risk_level.value}, "
                f"days_of_cover={inv.projected_days_of_cover}"
            )
        lines.append("")

    # Compliance
    if state.compliance_analyses:
        lines.append("## Compliance Overview (summarized)")
        for ca in state.compliance_analyses:
            label = f"Product {ca.product_id}" if ca.product_id else "Overall"
            lines.append(f"- {label}: {ca.summary}")
        lines.append("")

    # RAG context summary
    if state.rag_context:
        lines.append("## RAG Context")
        lines.append(
            f"- Marketplace: {state.rag_context.marketplace or 'any'}; "
            f"chunks={len(state.rag_context.chunks)}"
        )
        lines.append("")

    return "\n".join(lines)


@traceable_node("final_answer_agent")
def _call_final_answer_llm(prompt: str) -> FinalAnswerLLMOutput:
    """
    Internal LLM call wrapped with LangSmith tracing.
    """
    client = get_llm_client()
    return client.generate_structured(prompt, FinalAnswerLLMOutput)


def update_final_answer(state: SellerState) -> SellerState:
    """
    Final Answer Agent.

    Responsibilities:
      - Take the current SellerState, including ActionPlan and analyses.
      - Generate a clear, high-quality markdown answer for the seller.
      - Optionally refine the structured ActionPlan.
      - Attach FinalAnswer to state.final_answer.
    """
    final_prompt_template = load_prompt("final_answer")

    context_text = _build_final_context(state)
    default_citations = _build_citation_seeds(state)

    # We don't rely on fragile placeholders; we append a clearly delimited context.
    complete_prompt = (
        final_prompt_template
        + "\n\n"
        + "-----\n\n"
        + "## Structured Context for Final Answer\n\n"
        + context_text
        + "\n\n"
        + "## Existing Citation Seeds (for reference)\n\n"
        + "\n".join(f"- {c}" for c in default_citations)
    )

    logger.info("Final answer agent invoking LLM")

    try:
        llm_output = _call_final_answer_llm(complete_prompt)
    except LLMError as exc:
        # Fallback: keep the old, deterministic markdown composition style
        logger.error(
            "Final answer LLM call failed; falling back to simple composed answer",
            extra={"error": str(exc)},
        )

        summary_lines: List[str] = []

        if state.query is not None:
            summary_lines.append(f"### Query\n\n{state.query.raw_query}\n")

        if state.seller_profile is not None:
            summary_lines.append("### Seller Profile (Overview)\n")
            summary_lines.append(state.seller_profile.summary)

        if state.sales_analyses:
            summary_lines.append("### Sales Snapshot\n")
            for a in state.sales_analyses[:5]:
                summary_lines.append(f"- **Product** `{a.product_id}`: {a.narrative}")

        if state.competitor_analyses:
            summary_lines.append("### Competitor Snapshot\n")
            for c in state.competitor_analyses[:5]:
                summary_lines.append(
                    f"- **Product** `{c.product_id}`: {c.price_positioning}"
                )

        if state.inventory_analyses:
            summary_lines.append("### Inventory & Stock Risk\n")
            for inv in state.inventory_analyses[:5]:
                summary_lines.append(
                    f"- **Product** `{inv.product_id}`: {inv.narrative}"
                )

        if state.action_plan is not None:
            summary_lines.append("### Action Plan\n")
            summary_lines.append(state.action_plan.overall_summary)
        else:
            summary_lines.append("### Action Plan\n\nNo action plan is available yet.")

        answer_markdown = "\n\n".join(summary_lines)

        state.final_answer = FinalAnswer(
            answer_markdown=answer_markdown,
            action_plan=state.action_plan,
            citations=default_citations,
        )
        return state

    # Success path
    refined_plan = state.action_plan
    if llm_output.refined_action_plan is not None:
        refined_plan = _normalize_action_plan(llm_output.refined_action_plan)

    state.final_answer = FinalAnswer(
        answer_markdown=llm_output.answer_markdown,
        action_plan=refined_plan,
        citations=llm_output.citations or default_citations,
    )

    logger.info(
        "Final answer agent updated final_answer",
        extra={"num_citations": len(state.final_answer.citations)},
    )

    return state
