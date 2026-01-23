from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

from ..schemas.rag import RAGChunk


class QueryMode(str, Enum):
    """
    High-level modes for the copilot.

    This lets the router + planner adjust the workflow.
    """

    WEEKLY_PLAN = "weekly_plan"
    PRICING = "pricing"
    LISTING_SEO = "listing_seo"
    INVENTORY = "inventory"
    COMPLIANCE = "compliance"
    PROFITABILITY = "profitability"
    GENERAL_QA = "general_qa"


class QueryContext(BaseModel):
    """
    User's original query + resolved mode and scope.
    """

    model_config = ConfigDict(extra="ignore")

    raw_query: str = Field(
        ...,
        description="Original natural-language question from the seller.",
    )
    mode: QueryMode = Field(
        ...,
        description="Resolved intent/mode for this run.",
    )
    marketplaces: List[str] = Field(
        default_factory=list,
        description="Marketplaces in scope (e.g. ['amazon', 'flipkart']).",
    )
    language: str = Field(
        default="en",
        description="Language of the user's query/content.",
    )


class SellerProfile(BaseModel):
    """
    Lightweight profile of the seller aggregated from warehouse data.

    This is intentionally concise so it can be logged and passed between agents.
    """

    model_config = ConfigDict(extra="ignore")

    seller_id: Optional[str] = Field(
        default=None,
        description="Logical seller identifier; for now we can use a dummy or account id.",
    )
    total_products: int = Field(
        ge=0,
        description="Total number of products in the catalog for this seller.",
    )
    active_products: int = Field(
        ge=0,
        description="Number of active listings.",
    )
    marketplaces: List[str] = Field(
        default_factory=list,
        description="Marketplaces where the seller currently has listings.",
    )
    primary_categories: List[str] = Field(
        default_factory=list,
        description="Top-level categories this seller primarily operates in.",
    )
    summary: str = Field(
        default="",
        description="Short, LLM-generated description of the seller's situation.",
    )


class ProductFilter(BaseModel):
    """
    High-level filter used to decide which products are in scope.
    """

    model_config = ConfigDict(extra="ignore")

    product_ids: Optional[List[str]] = Field(
        default=None,
        description="Explicit product_ids requested by the user, if any.",
    )
    category: Optional[str] = Field(
        default=None,
        description="Focus on a specific category (e.g. 'shoes').",
    )
    marketplace: Optional[str] = Field(
        default=None,
        description="Focus on a single marketplace, if requested.",
    )


class ProductSelection(BaseModel):
    """
    Final list of products in scope for this run, plus the filter used.
    """

    model_config = ConfigDict(extra="ignore")

    filter: ProductFilter = Field(
        default_factory=ProductFilter,
        description="Filter parameters that led to this selection.",
    )
    selected_product_ids: List[str] = Field(
        default_factory=list,
        description="Product IDs that downstream agents should operate on.",
    )
    notes: str = Field(
        default="",
        description="LLM reasoning about why these products were selected.",
    )


class SalesAnalysis(BaseModel):
    """
    Summary of sales performance for a single product.
    """

    model_config = ConfigDict(extra="ignore")

    product_id: str
    total_units_sold: int = Field(ge=0)
    total_gross_revenue: float = Field(ge=0)
    total_returns: int = Field(ge=0)
    total_page_views: int = Field(ge=0)
    avg_selling_price: Optional[float] = Field(default=None, ge=0)
    conversion_rate: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="Approximate units_sold / page_views.",
    )
    narrative: str = Field(
        default="",
        description="LLM-written narrative summarizing sales performance.",
    )


class CompetitorAnalysis(BaseModel):
    """
    Summary of competitor landscape for a product.
    """

    model_config = ConfigDict(extra="ignore")

    product_id: str
    num_competitors: int = Field(ge=0)
    avg_competitor_price: Optional[float] = Field(default=None, ge=0)
    seller_avg_price: Optional[float] = Field(default=None, ge=0)
    price_positioning: str = Field(
        default="",
        description="LLM description of price positioning vs competitors.",
    )
    notes: str = Field(
        default="",
        description="Any additional insights (e.g. fulfillment types, ratings).",
    )


class InventoryRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InventoryAnalysis(BaseModel):
    """
    Stock and demand risk analysis for a product.
    """

    model_config = ConfigDict(extra="ignore")

    product_id: str
    current_stock: int = Field(ge=0)
    reorder_level: int = Field(ge=0)
    projected_days_of_cover: Optional[float] = Field(
        default=None,
        description="Estimated days before stockout at current demand.",
    )
    risk_level: InventoryRiskLevel = Field(
        default=InventoryRiskLevel.LOW,
        description="Qualitative risk classification.",
    )
    narrative: str = Field(
        default="",
        description="LLM commentary on stock / overstock / stockout risk.",
    )


class ComplianceIssueSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKING = "blocking"


class ComplianceIssue(BaseModel):
    """
    A single potential compliance/policy issue detected via RAG.
    """

    model_config = ConfigDict(extra="ignore")

    code: str = Field(
        ...,
        description="Short machine-readable identifier (e.g. 'IMAGE_BACKGROUND', 'RESTRICTED_WORD').",
    )
    severity: ComplianceIssueSeverity = Field(
        default=ComplianceIssueSeverity.MEDIUM,
    )
    message: str = Field(
        ...,
        description="Human-readable description of the issue.",
    )
    marketplace: Optional[str] = Field(
        default=None,
        description="Marketplace this issue applies to.",
    )
    section: Optional[str] = Field(
        default=None,
        description="Policy section from which this issue was derived.",
    )
    citation_sources: List[str] = Field(
        default_factory=list,
        description="List of RAG source identifiers used as evidence.",
    )


class ComplianceAnalysis(BaseModel):
    """
    Aggregate view of compliance risks for a product or listing set.
    """

    model_config = ConfigDict(extra="ignore")

    product_id: Optional[str] = None
    issues: List[ComplianceIssue] = Field(default_factory=list)
    summary: str = Field(
        default="",
        description="LLM summary of compliance posture and recommendations.",
    )


class PricingSuggestion(BaseModel):
    """
    Suggested price change for a product.
    """

    model_config = ConfigDict(extra="ignore")

    product_id: str
    current_price: Optional[float] = Field(default=None, ge=0)
    suggested_price: Optional[float] = Field(default=None, ge=0)
    expected_margin_change: Optional[float] = Field(
        default=None,
        description="Estimated change in margin in absolute terms or percentage.",
    )
    rationale: str = Field(
        default="",
        description="Explanation of why this price change is recommended.",
    )


class ProfitabilityAnalysis(BaseModel):
    """
    Profitability summary for a product or a small group of products.
    """

    model_config = ConfigDict(extra="ignore")

    product_id: Optional[str] = None
    estimated_net_margin_percent: Optional[float] = Field(
        default=None,
        description="Approximate net margin percentage.",
    )
    key_drivers: str = Field(
        default="",
        description="Narrative of what drives margin (fees, ads, returns, etc.).",
    )


class ListingSEOAnalysis(BaseModel):
    """
    Listing/SEO quality analysis for a product.
    """

    model_config = ConfigDict(extra="ignore")

    product_id: str
    title_score: Optional[float] = Field(default=None, ge=0, le=1)
    bullets_score: Optional[float] = Field(default=None, ge=0, le=1)
    images_score: Optional[float] = Field(default=None, ge=0, le=1)
    keywords_coverage_score: Optional[float] = Field(default=None, ge=0, le=1)
    recommendations: str = Field(
        default="",
        description="Concrete recommendations to improve title, bullets, images, SEO.",
    )


class RAGContext(BaseModel):
    """
    RAG results that were actually used to answer this query.
    """

    model_config = ConfigDict(extra="ignore")

    query: str = Field(
        ...,
        description="Canonical RAG query used to fetch policy/guideline chunks.",
    )
    marketplace: Optional[str] = Field(
        default=None,
        description="Marketplace filter applied for RAG, if any.",
    )
    section: Optional[str] = Field(
        default=None,
        description="Section filter applied for RAG, if any.",
    )
    chunks: List[RAGChunk] = Field(
        default_factory=list,
        description="Chunks actually fed into LLM prompts.",
    )


class ActionPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionCategory(str, Enum):
    PRICING = "pricing"
    LISTING = "listing"
    SEO = "seo"
    INVENTORY = "inventory"
    COMPLIANCE = "compliance"
    PROFITABILITY = "profitability"
    OTHER = "other"


class ActionItem(BaseModel):
    """
    A single recommended action in the weekly plan / output.
    """

    model_config = ConfigDict(extra="ignore")

    id: str = Field(
        ...,
        description="Stable identifier for this action within the plan.",
    )
    product_id: Optional[str] = Field(
        default=None,
        description="Product this action is associated with, if any.",
    )
    title: str = Field(
        ...,
        description="One-line summary of the action.",
    )
    description: str = Field(
        ...,
        description="Detailed explanation of what to do and why.",
    )
    category: ActionCategory = Field(default=ActionCategory.OTHER)
    priority: ActionPriority = Field(default=ActionPriority.MEDIUM)
    timeframe: Optional[str] = Field(
        default=None,
        description="Suggested timeline (e.g. 'this week', 'next 2 days').",
    )
    estimated_impact: Optional[str] = Field(
        default=None,
        description="Brief description of expected business impact.",
    )
    blocking: bool = Field(
        default=False,
        description="If True, this action unblocks or protects other work.",
    )


class ActionPlan(BaseModel):
    """
    Aggregate of all recommended actions for the seller.
    """

    model_config = ConfigDict(extra="ignore")

    overall_summary: str = Field(
        default="",
        description="High-level summary of the action plan.",
    )
    actions: List[ActionItem] = Field(
        default_factory=list,
        description="Prioritized list of actions.",
    )


class Critique(BaseModel):
    """
    Reflections/criticisms over the current plan/answer from a critic agent.
    """

    model_config = ConfigDict(extra="ignore")

    comments: str = Field(
        default="",
        description="Free-form critique of the current answer/plan.",
    )
    detected_risks: List[str] = Field(
        default_factory=list,
        description="Risks or edge cases the critic agent identified.",
    )
    missing_elements: List[str] = Field(
        default_factory=list,
        description="Notable things that are missing from the solution.",
    )
    score: Optional[float] = Field(
        default=None,
        description="Optional quality score (0–1 or 0–10 depending on design).",
    )


class FinalAnswer(BaseModel):
    """
    Final user-facing answer, ready to be returned by the API.

    This is what we will serialize as the main response body.
    """

    model_config = ConfigDict(extra="ignore")

    answer_markdown: str = Field(
        ...,
        description="Markdown-formatted answer summarizing all analyses and actions.",
    )
    action_plan: Optional[ActionPlan] = Field(
        default=None,
        description="Structured plan included in the final answer, if applicable.",
    )
    citations: List[str] = Field(
        default_factory=list,
        description="Optional list of citations/IDs corresponding to RAG sources.",
    )


class HITLFeedback(BaseModel):
    """
    Human-in-the-loop feedback to close the loop for learning/improvement.
    """

    model_config = ConfigDict(extra="ignore")

    rating: Optional[int] = Field(
        default=None,
        ge=1,
        le=5,
        description="High-level rating from the user (e.g., 1–5).",
    )
    comments: Optional[str] = Field(
        default=None,
        description="Free-text feedback from the user.",
    )
    selected_action_ids: List[str] = Field(
        default_factory=list,
        description="Actions the user accepted/committed to.",
    )
    discarded_action_ids: List[str] = Field(
        default_factory=list,
        description="Actions the user explicitly rejected.",
    )


class SellerState(BaseModel):
    """
    Shared, serializable state for the multi-agent LangGraph.

    Each agent reads and writes a subset of these fields.
    """

    model_config = ConfigDict(extra="ignore")

    # Input / routing
    query: Optional[QueryContext] = None
    seller_profile: Optional[SellerProfile] = None
    product_selection: Optional[ProductSelection] = None

    # Analyses (per product)
    sales_analyses: List[SalesAnalysis] = Field(default_factory=list)
    competitor_analyses: List[CompetitorAnalysis] = Field(default_factory=list)
    inventory_analyses: List[InventoryAnalysis] = Field(default_factory=list)
    compliance_analyses: List[ComplianceAnalysis] = Field(default_factory=list)
    pricing_suggestions: List[PricingSuggestion] = Field(default_factory=list)
    profitability_analyses: List[ProfitabilityAnalysis] = Field(default_factory=list)
    listing_seo_analyses: List[ListingSEOAnalysis] = Field(default_factory=list)

    # RAG + planning + outputs
    rag_context: Optional[RAGContext] = None
    action_plan: Optional[ActionPlan] = None
    critique: Optional[Critique] = None
    final_answer: Optional[FinalAnswer] = None

    # Human-in-the-loop feedback
    hitl_feedback: Optional[HITLFeedback] = None
