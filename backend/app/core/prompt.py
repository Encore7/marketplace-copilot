from functools import lru_cache
from pathlib import Path

from .config import settings

PROMPT_ROOT = Path(__file__).resolve().parents[3] / "prompts"


@lru_cache(maxsize=32)
def load_prompt(agent: str, version: str = None) -> str:
    """Load the prompt template for a given agent and version."""
    if version is None:
        attr = f"{agent}_prompt_version"
        version = getattr(settings, attr, "v1")

    path = PROMPT_ROOT / agent / f"{version}.md"
    with path.open("r", encoding="utf-8") as f:
        return f.read()
