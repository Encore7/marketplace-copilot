from backend.app.agents.listing_agent import update_listing_and_seo_actions
from backend.app.agents.pricing_agent import update_pricing_recommendations
from backend.app.agents.profit_agent import update_profit_summary
from backend.app.agents.state import SellerState


def test_agents_create_schema_compatible_actions():
    state = SellerState()

    state = update_listing_and_seo_actions(state)
    state = update_pricing_recommendations(state)
    state = update_profit_summary(state)

    # The agents should not crash when there is insufficient data
    # and should preserve schema-valid action_plan structure.
    if state.action_plan is not None:
        for action in state.action_plan.actions:
            assert action.id
            assert action.category is not None
            assert action.priority is not None
