from backend.app.agents.planner_agent import (
    PlannerLLMAction,
    PlannerLLMActionPlan,
    _normalize_action_plan,
)
from backend.app.agents.state import ActionCategory, ActionPriority


def test_planner_action_normalization_maps_fields():
    plan = PlannerLLMActionPlan(
        overall_summary="summary",
        actions=[
            PlannerLLMAction(
                area="pricing",
                title="Adjust price",
                description="Reason",
                priority="high",
                impact="medium",
                product_id="P1",
            )
        ],
    )

    normalized = _normalize_action_plan(plan)
    assert normalized.actions[0].category == ActionCategory.PRICING
    assert normalized.actions[0].priority == ActionPriority.HIGH
    assert normalized.actions[0].estimated_impact == "medium"
