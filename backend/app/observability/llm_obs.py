from __future__ import annotations

import os
from typing import Any, Callable, Optional

from ..core.config import settings

try:
    from langsmith import Client
    from langsmith import traceable
except Exception:  # pragma: no cover - optional dependency
    Client = None  # type: ignore[assignment]
    traceable = None  # type: ignore[assignment]

_langsmith_client: Optional["Client"] = None


def get_langsmith_client() -> Optional["Client"]:
    """
    Lazily initialize and return a LangSmith client if API key is configured.
    """
    global _langsmith_client

    if Client is None:
        return None

    if _langsmith_client is not None:
        return _langsmith_client

    if not settings.llm_obs.tracing_v2:
        return None

    if not settings.llm_obs.langsmith_api_key:
        return None

    # Ensure LangSmith runtime env aligns with app settings.
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_PROJECT"] = (
        settings.llm_obs.langsmith_project or "marketplace-copilot"
    )
    os.environ["LANGSMITH_API_KEY"] = settings.llm_obs.langsmith_api_key

    _langsmith_client = Client(
        api_key=settings.llm_obs.langsmith_api_key,
    )
    return _langsmith_client


def traceable_node(name: str) -> Callable[..., Any]:
    """
    Decorator factory for LangGraph nodes / LLM-invoking functions.

    Usage:
        @traceable_node("planner_agent")
        def run_planner(...): ...
    """
    client = get_langsmith_client()
    if client is None or traceable is None:
        # Fallback: no-op decorator if LangSmith is not configured.
        def noop_decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return func

        return noop_decorator

    return traceable(
        name=name,
        client=client,
        project_name=settings.llm_obs.langsmith_project or "marketplace-copilot",
    )
