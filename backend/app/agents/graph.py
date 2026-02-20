from __future__ import annotations

from typing import Any, Dict, List

from langgraph.graph import END, StateGraph

from ..observability.llm_obs import traceable_node
from ..observability.logging import get_logger
from .competitor_agent import update_competitor_analyses
from .compliance_agent import update_compliance_and_rag
from .critic_agent import update_critique
from .final_answer_agent import update_final_answer
from .graph_state import GraphState, graph_state_to_seller_state
from .hitl_agent import initialize_hitl_feedback
from .inventory_agent import update_inventory_analyses
from .listing_agent import update_listing_and_seo_actions
from .planner_agent import update_action_plan
from .pricing_agent import update_pricing_recommendations
from .product_selector_agent import update_product_selection
from .profile_agent import update_seller_profile
from .profit_agent import update_profit_summary
from .rag_agent import update_rag_context
from .router_agent import update_query_routing
from .sales_agent import update_sales_analyses
from .state import ActionPlan, QueryContext, QueryMode, SellerState

logger = get_logger("agents.graph")


def _to_seller_state(state: GraphState) -> SellerState:
    return graph_state_to_seller_state(state)


def _record_step(
    node_name: str,
    tools: list[str] | None = None,
) -> List[str]:
    tools_part = f" tools={','.join(tools)}" if tools else ""
    return [f"agent={node_name}{tools_part}"]


def _record_skip(node_name: str, reason: str) -> List[str]:
    return [f"agent={node_name} skipped reason={reason}"]


def _intent(state: GraphState, key: str) -> bool:
    query = state.get("query")
    if query is None:
        return False
    if isinstance(query, dict):
        query = QueryContext.model_validate(query)
    return bool(query.intent_flags.get(key, False))


_ANALYSIS_BRANCHES: List[str] = ["sales", "competitor", "inventory", "rag"]
_ACTION_BRANCHES: List[str] = ["listing", "pricing", "profit"]


def _dedupe_actions(actions: List[Any]) -> List[Any]:
    seen: set[str] = set()
    out: List[Any] = []
    for action in actions:
        aid = getattr(action, "id", "") or ""
        if aid:
            if aid in seen:
                continue
            seen.add(aid)
        out.append(action)
    return out


@traceable_node("graph.router")
def router_node(state: GraphState) -> Dict[str, Any]:
    seller_state = _to_seller_state(state)

    if seller_state.query is None:
        raw_query = state.get("raw_query") or state.get("query_text") or ""
        if not raw_query:
            raise ValueError("SellerState.query is missing and no raw query was provided.")
        seller_state.query = QueryContext(
            raw_query=raw_query,
            mode=QueryMode.GENERAL_QA,
            marketplaces=[],
        )

    seller_state = update_query_routing(seller_state)
    return {
        "query": seller_state.query,
        "execution_trace": _record_step("router", tools=["router_agent"]),
    }


@traceable_node("graph.seller_profile")
def seller_profile_node(state: GraphState) -> Dict[str, Any]:
    seller_state = _to_seller_state(state)
    seller_state = update_seller_profile(seller_state)
    return {
        "seller_profile": seller_state.seller_profile,
        "execution_trace": _record_step("seller_profile", tools=["seller_repository"]),
    }


@traceable_node("graph.product_selector")
def product_selector_node(state: GraphState) -> Dict[str, Any]:
    seller_state = _to_seller_state(state)
    seller_state = update_product_selection(seller_state)
    return {
        "product_selection": seller_state.product_selection,
        "execution_trace": _record_step("product_selector", tools=["seller_repository"]),
    }


@traceable_node("graph.analysis_dispatch")
def analysis_dispatch_node(state: GraphState) -> Dict[str, Any]:
    query = state.get("query")
    if query is None:
        return {"execution_trace": _record_step("analysis_dispatch")}
    if isinstance(query, dict):
        query = QueryContext.model_validate(query)

    active: List[str] = []
    if bool(query.intent_flags.get("need_sales")):
        active.append("sales")
    if bool(query.intent_flags.get("need_competitor")):
        active.append("competitor")
    if bool(query.intent_flags.get("need_inventory")):
        active.append("inventory")
    if bool(query.intent_flags.get("need_rag")) or bool(query.intent_flags.get("need_compliance")):
        active.append("rag")

    skipped = [branch for branch in _ANALYSIS_BRANCHES if branch not in active]
    trace = _record_step("analysis_dispatch")
    for branch in skipped:
        trace.extend(_record_skip(branch, "intent_not_required"))

    return {
        "query": query,
        "active_branches": active,
        "skipped_branches": skipped,
        "execution_trace": trace,
    }


def _analysis_targets(state: GraphState) -> List[str]:
    targets: List[str] = []
    if _intent(state, "need_sales"):
        targets.append("sales")
    if _intent(state, "need_competitor"):
        targets.append("competitor")
    if _intent(state, "need_inventory"):
        targets.append("inventory")
    if _intent(state, "need_rag") or _intent(state, "need_compliance"):
        targets.append("rag")
    return targets or ["analysis_join"]


@traceable_node("graph.sales")
def sales_node(state: GraphState) -> Dict[str, Any]:
    seller_state = _to_seller_state(state)
    seller_state = update_sales_analyses(seller_state)
    return {
        "sales_analyses": seller_state.sales_analyses,
        "execution_trace": _record_step("sales", tools=["sales_tool"]),
    }


@traceable_node("graph.competitor")
def competitor_node(state: GraphState) -> Dict[str, Any]:
    seller_state = _to_seller_state(state)
    seller_state = update_competitor_analyses(seller_state)
    return {
        "competitor_analyses": seller_state.competitor_analyses,
        "execution_trace": _record_step("competitor", tools=["competitor_tool"]),
    }


@traceable_node("graph.inventory")
def inventory_node(state: GraphState) -> Dict[str, Any]:
    seller_state = _to_seller_state(state)
    seller_state = update_inventory_analyses(seller_state)
    return {
        "inventory_analyses": seller_state.inventory_analyses,
        "execution_trace": _record_step("inventory", tools=["demand_tool"]),
    }


@traceable_node("graph.rag")
async def rag_node(state: GraphState) -> Dict[str, Any]:
    seller_state = _to_seller_state(state)
    seller_state = await update_rag_context(seller_state)
    return {
        "rag_context": seller_state.rag_context,
        "execution_trace": _record_step("rag", tools=["rag_tool"]),
    }


def _rag_targets(state: GraphState) -> List[str]:
    if _intent(state, "need_compliance"):
        return ["compliance"]
    return ["analysis_join"]


@traceable_node("graph.compliance")
async def compliance_node(state: GraphState) -> Dict[str, Any]:
    seller_state = _to_seller_state(state)
    seller_state = await update_compliance_and_rag(seller_state)
    return {
        "rag_context": seller_state.rag_context,
        "compliance_analyses": seller_state.compliance_analyses,
        "execution_trace": _record_step("compliance", tools=["rag_tool"]),
    }


@traceable_node("graph.analysis_join")
def analysis_join_node(state: GraphState) -> Dict[str, Any]:
    return {"execution_trace": _record_step("analysis_join")}


@traceable_node("graph.planner")
def planner_node(state: GraphState) -> Dict[str, Any]:
    seller_state = _to_seller_state(state)
    seller_state = update_action_plan(seller_state)
    return {
        "action_plan": seller_state.action_plan,
        "listing_branch_actions": [],
        "pricing_branch_actions": [],
        "profit_branch_actions": [],
        "execution_trace": _record_step("planner", tools=["llm"]),
    }


@traceable_node("graph.action_dispatch")
def action_dispatch_node(state: GraphState) -> Dict[str, Any]:
    query = state.get("query")
    if query is None:
        return {"execution_trace": _record_step("action_dispatch")}
    if isinstance(query, dict):
        query = QueryContext.model_validate(query)

    active: List[str] = []
    if bool(query.intent_flags.get("need_listing_seo")):
        active.append("listing")
    if bool(query.intent_flags.get("need_pricing")):
        active.append("pricing")
    if bool(query.intent_flags.get("need_profit")):
        active.append("profit")
    skipped = [branch for branch in _ACTION_BRANCHES if branch not in active]

    trace = _record_step("action_dispatch")
    for branch in skipped:
        trace.extend(_record_skip(branch, "intent_not_required"))

    return {
        "query": query,
        "active_branches": active,
        "skipped_branches": skipped,
        "execution_trace": trace,
    }


def _action_targets(state: GraphState) -> List[str]:
    targets: List[str] = []
    if _intent(state, "need_listing_seo"):
        targets.append("listing")
    if _intent(state, "need_pricing"):
        targets.append("pricing")
    if _intent(state, "need_profit"):
        targets.append("profit")
    return targets or ["action_join"]


@traceable_node("graph.listing")
def listing_node(state: GraphState) -> Dict[str, Any]:
    seller_state = _to_seller_state(state)
    before_ids = {a.id for a in (seller_state.action_plan.actions if seller_state.action_plan else [])}
    tmp = seller_state.model_copy(deep=True)
    tmp = update_listing_and_seo_actions(tmp)
    additions = []
    if tmp.action_plan is not None:
        additions = [a for a in tmp.action_plan.actions if a.id not in before_ids]
    return {
        "listing_branch_actions": additions,
        "execution_trace": _record_step("listing", tools=["seo_tool"]),
    }


@traceable_node("graph.pricing")
def pricing_node(state: GraphState) -> Dict[str, Any]:
    seller_state = _to_seller_state(state)
    before_ids = {a.id for a in (seller_state.action_plan.actions if seller_state.action_plan else [])}
    tmp = seller_state.model_copy(deep=True)
    tmp = update_pricing_recommendations(tmp)
    additions = []
    if tmp.action_plan is not None:
        additions = [a for a in tmp.action_plan.actions if a.id not in before_ids]
    return {
        "pricing_branch_actions": additions,
        "execution_trace": _record_step("pricing", tools=["profit_tool"]),
    }


@traceable_node("graph.profit")
def profit_node(state: GraphState) -> Dict[str, Any]:
    seller_state = _to_seller_state(state)
    before_ids = {a.id for a in (seller_state.action_plan.actions if seller_state.action_plan else [])}
    tmp = seller_state.model_copy(deep=True)
    tmp = update_profit_summary(tmp)
    additions = []
    if tmp.action_plan is not None:
        additions = [a for a in tmp.action_plan.actions if a.id not in before_ids]
    return {
        "profit_branch_actions": additions,
        "execution_trace": _record_step("profit", tools=["profit_tool"]),
    }


@traceable_node("graph.action_join")
def action_join_node(state: GraphState) -> Dict[str, Any]:
    seller_state = _to_seller_state(state)
    if seller_state.action_plan is None:
        seller_state.action_plan = ActionPlan(overall_summary="", actions=[])

    merged = list(seller_state.action_plan.actions)
    merged.extend(seller_state.listing_branch_actions)
    merged.extend(seller_state.pricing_branch_actions)
    merged.extend(seller_state.profit_branch_actions)
    seller_state.action_plan.actions = _dedupe_actions(merged)
    return {
        "action_plan": seller_state.action_plan,
        "execution_trace": _record_step("action_join"),
    }


@traceable_node("graph.critic")
def critic_node(state: GraphState) -> Dict[str, Any]:
    seller_state = _to_seller_state(state)
    seller_state = update_critique(seller_state)
    return {
        "critique": seller_state.critique,
        "execution_trace": _record_step("critic", tools=["llm"]),
    }


@traceable_node("graph.final_answer")
def final_answer_node(state: GraphState) -> Dict[str, Any]:
    seller_state = _to_seller_state(state)
    seller_state = update_final_answer(seller_state)
    return {
        "final_answer": seller_state.final_answer,
        "execution_trace": _record_step("final_answer", tools=["llm"]),
    }


@traceable_node("graph.hitl")
def hitl_node(state: GraphState) -> Dict[str, Any]:
    seller_state = _to_seller_state(state)
    seller_state = initialize_hitl_feedback(seller_state)
    return {
        "hitl_feedback": seller_state.hitl_feedback,
        "execution_trace": _record_step("hitl"),
    }


def create_copilot_graph() -> Any:
    graph = StateGraph(GraphState)

    graph.add_node("router", router_node)
    graph.add_node("seller_profile", seller_profile_node)
    graph.add_node("product_selector", product_selector_node)
    graph.add_node("analysis_dispatch", analysis_dispatch_node)
    graph.add_node("sales", sales_node)
    graph.add_node("competitor", competitor_node)
    graph.add_node("inventory", inventory_node)
    graph.add_node("rag", rag_node)
    graph.add_node("compliance", compliance_node)
    graph.add_node("analysis_join", analysis_join_node)
    graph.add_node("planner", planner_node)
    graph.add_node("action_dispatch", action_dispatch_node)
    graph.add_node("listing", listing_node)
    graph.add_node("pricing", pricing_node)
    graph.add_node("profit", profit_node)
    graph.add_node("action_join", action_join_node)
    graph.add_node("critic", critic_node)
    graph.add_node("final_answer", final_answer_node)
    graph.add_node("hitl", hitl_node)

    graph.set_entry_point("router")
    graph.add_edge("router", "seller_profile")
    graph.add_edge("seller_profile", "product_selector")
    graph.add_edge("product_selector", "analysis_dispatch")

    graph.add_conditional_edges(
        "analysis_dispatch",
        _analysis_targets,
        ["sales", "competitor", "inventory", "rag", "analysis_join"],
    )
    graph.add_edge("sales", "analysis_join")
    graph.add_edge("competitor", "analysis_join")
    graph.add_edge("inventory", "analysis_join")
    graph.add_conditional_edges("rag", _rag_targets, ["compliance", "analysis_join"])
    graph.add_edge("compliance", "analysis_join")

    graph.add_edge("analysis_join", "planner")
    graph.add_edge("planner", "action_dispatch")
    graph.add_conditional_edges(
        "action_dispatch",
        _action_targets,
        ["listing", "pricing", "profit", "action_join"],
    )
    graph.add_edge("listing", "action_join")
    graph.add_edge("pricing", "action_join")
    graph.add_edge("profit", "action_join")

    graph.add_edge("action_join", "critic")
    graph.add_edge("critic", "final_answer")
    graph.add_edge("final_answer", "hitl")
    graph.add_edge("hitl", END)

    return graph.compile()
