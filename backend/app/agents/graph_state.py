from __future__ import annotations

import operator
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from .state import (
    ActionItem,
    ActionPlan,
    ComplianceAnalysis,
    Critique,
    FinalAnswer,
    HITLFeedback,
    InventoryAnalysis,
    ProductSelection,
    QueryContext,
    SellerProfile,
    SellerState,
    SalesAnalysis,
    CompetitorAnalysis,
    RAGContext,
)


def _merge_by_product_id(existing: List[Any], incoming: List[Any]) -> List[Any]:
    out: Dict[Optional[str], Any] = {}
    for item in existing:
        out[getattr(item, "product_id", None)] = item
    for item in incoming:
        out[getattr(item, "product_id", None)] = item
    return list(out.values())


def _merge_action_items(existing: List[ActionItem], incoming: List[ActionItem]) -> List[ActionItem]:
    out: Dict[str, ActionItem] = {a.id: a for a in existing if a.id}
    ordered: List[ActionItem] = list(existing)
    for action in incoming:
        if action.id and action.id in out:
            continue
        ordered.append(action)
        if action.id:
            out[action.id] = action
    return ordered


def _merge_dict(existing: Dict[str, float], incoming: Dict[str, float]) -> Dict[str, float]:
    merged = dict(existing)
    merged.update(incoming)
    return merged


def _union_strings(existing: List[str], incoming: List[str]) -> List[str]:
    seen = set(existing)
    out = list(existing)
    for item in incoming:
        if item not in seen:
            out.append(item)
            seen.add(item)
    return out


class GraphState(TypedDict, total=False):
    # Input/routing
    query: QueryContext
    seller_profile: SellerProfile
    product_selection: ProductSelection

    # Analysis channels
    sales_analyses: Annotated[List[SalesAnalysis], _merge_by_product_id]
    competitor_analyses: Annotated[List[CompetitorAnalysis], _merge_by_product_id]
    inventory_analyses: Annotated[List[InventoryAnalysis], _merge_by_product_id]
    compliance_analyses: Annotated[List[ComplianceAnalysis], _merge_by_product_id]
    rag_context: RAGContext

    # Planning/action channels
    action_plan: ActionPlan
    listing_branch_actions: Annotated[List[ActionItem], _merge_action_items]
    pricing_branch_actions: Annotated[List[ActionItem], _merge_action_items]
    profit_branch_actions: Annotated[List[ActionItem], _merge_action_items]

    # Outputs
    critique: Critique
    final_answer: FinalAnswer
    hitl_feedback: HITLFeedback

    # Observability/control
    execution_trace: Annotated[List[str], operator.add]
    active_branches: Annotated[List[str], _union_strings]
    skipped_branches: Annotated[List[str], _union_strings]
    answer_quality_signals: Annotated[Dict[str, float], _merge_dict]


def seller_state_to_graph_state(state: SellerState) -> GraphState:
    return state.model_dump()  # type: ignore[return-value]


def graph_state_to_seller_state(state: GraphState) -> SellerState:
    return SellerState.model_validate(state)
