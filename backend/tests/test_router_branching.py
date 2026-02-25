from backend.app.agents.router_agent import update_query_routing
from backend.app.agents.state import QueryContext, QueryMode, SellerState


def test_router_mode_pricing_enables_pricing_branches():
    state = SellerState(
        query=QueryContext(
            raw_query="Help me reprice this SKU for better margin",
            mode=QueryMode.PRICING,
            marketplaces=["amazon"],
        )
    )
    out = update_query_routing(state)
    flags = out.query.intent_flags

    assert flags["need_sales"] is True
    assert flags["need_competitor"] is True
    assert flags["need_pricing"] is True
    assert flags["need_profit"] is True
    assert "pricing" in out.query.requested_capabilities
    assert 0.0 <= out.query.routing_confidence <= 1.0


def test_router_mode_compliance_enables_rag_and_compliance():
    state = SellerState(
        query=QueryContext(
            raw_query="Check compliance for my listings",
            mode=QueryMode.COMPLIANCE,
            marketplaces=[],
        )
    )
    out = update_query_routing(state)
    flags = out.query.intent_flags

    assert flags["need_rag"] is True
    assert flags["need_compliance"] is True
    assert "compliance" in out.query.requested_capabilities
    assert out.query.marketplaces


def test_router_general_qa_keyword_overlays_mixed_intent():
    state = SellerState(
        query=QueryContext(
            raw_query="Improve margin and avoid policy violations for image/title",
            mode=QueryMode.GENERAL_QA,
            marketplaces=["amazon"],
        )
    )
    out = update_query_routing(state)
    flags = out.query.intent_flags

    assert flags["need_pricing"] is True
    assert flags["need_profit"] is True
    assert flags["need_compliance"] is True
    assert flags["need_rag"] is True
    assert flags["need_listing_seo"] is True
