from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict

from .config import settings

# Root of the repo → prompts directory
PROMPT_ROOT = Path(__file__).resolve().parents[3] / "prompts"


_AGENT_TO_VERSION_ATTR: Dict[str, str] = {
    # agent_name_in_code: attribute_name_on_settings_for_version
    "planner": "planner_prompt_version",
    "critic": "critic_prompt_version",
    "final_answer": "final_answer_prompt_version",
    "listing_agent": "listing_agent_prompt_version",
    "pricing_agent": "pricing_agent_prompt_version",
    "compliance_agent": "compliance_agent_prompt_version",
    "inventory_agent": "inventory_agent_prompt_version",
    "profit_agent": "profit_agent_prompt_version",
    # we will add more agents here as needed
}


def _resolve_version(agent: str, override: str | None) -> str:
    """
    Resolve the prompt version for a given agent.

    Priority:
    1) Explicit override passed in (version arg)
    2) settings.<agent>_prompt_version (env-driven)
    3) Default "v1"
    """
    if override is not None:
        return override

    attr_name = _AGENT_TO_VERSION_ATTR.get(agent)
    if attr_name is not None:
        version = getattr(settings, attr_name, None)
        if version:
            return version

    # Fallback
    return "v1"


@lru_cache(maxsize=32)
def load_prompt(agent: str, version: str | None = None) -> str:
    """
    Load the prompt template for a given agent and version.

    File layout (flat):
        prompts/{agent}_{version}.md

    Examples:
        load_prompt("planner") -> prompts/planner_v1.md (by default)
        load_prompt("planner", "v2") -> prompts/planner_v2.md
    """
    resolved_version = _resolve_version(agent, version)
    filename = f"{agent}_{resolved_version}.md"
    path = PROMPT_ROOT / filename

    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")

    return path.read_text(encoding="utf-8")
