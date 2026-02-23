from backend.app.agents.graph import (
    _action_targets,
    _analysis_targets,
    action_dispatch_node,
    analysis_dispatch_node,
)
from backend.app.agents.state import QueryContext, QueryMode, SellerState


def _state_with_flags(flags: dict[str, bool]) -> dict:
    return SellerState(
        query=QueryContext(
            raw_query="test",
            mode=QueryMode.GENERAL_QA,
            marketplaces=["amazon"],
            intent_flags=flags,
            requested_capabilities=[],
            routing_confidence=0.7,
        )
    ).model_dump()


def test_analysis_targets_select_expected_nodes():
    state = _state_with_flags(
        {
            "need_sales": True,
            "need_competitor": False,
            "need_inventory": True,
            "need_pricing": False,
            "need_profit": False,
            "need_listing_seo": False,
            "need_compliance": False,
            "need_rag": True,
        }
    )
    targets = _analysis_targets(state)
    assert targets == ["sales", "inventory", "rag"]


def test_action_targets_fallback_to_join_when_none():
    state = _state_with_flags(
        {
            "need_sales": True,
            "need_competitor": False,
            "need_inventory": False,
            "need_pricing": False,
            "need_profit": False,
            "need_listing_seo": False,
            "need_compliance": False,
            "need_rag": False,
        }
    )
    targets = _action_targets(state)
    assert targets == ["action_join"]


def test_dispatch_nodes_record_skipped_branches():
    state = _state_with_flags(
        {
            "need_sales": True,
            "need_competitor": False,
            "need_inventory": False,
            "need_pricing": True,
            "need_profit": False,
            "need_listing_seo": False,
            "need_compliance": False,
            "need_rag": False,
        }
    )

    after_analysis = analysis_dispatch_node(state)
    trace = after_analysis["execution_trace"]
    assert any("agent=competitor skipped reason=intent_not_required" in t for t in trace)
    assert any("agent=inventory skipped reason=intent_not_required" in t for t in trace)

    after_action = action_dispatch_node(after_analysis)
    trace2 = after_action["execution_trace"]
    assert any("agent=listing skipped reason=intent_not_required" in t for t in trace2)
    assert any("agent=profit skipped reason=intent_not_required" in t for t in trace2)
