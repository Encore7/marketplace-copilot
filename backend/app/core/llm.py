from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, Optional, Type, TypeVar

import httpx
from pydantic import BaseModel

from ..observability.logging import get_logger
from .config import settings

logger = get_logger("core.llm")

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """Raised when the LLM provider returns an error or invalid response."""


class LLMClient:
    """
    Minimal LLM client abstraction.

    For now, supports:
      - provider = "ollama"
      - chat-style calls
    """

    def __init__(
        self,
        provider: str,
        model: str,
    ) -> None:
        self.provider = provider
        self.model = model

    # public API

    def generate_structured(
        self,
        prompt: str,
        output_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> T:
        """
        Generate a structured response that conforms to `output_model`.

        The LLM is instructed to respond in pure JSON that can be parsed into
        the target Pydantic model.
        """
        if self.provider == "ollama":
            raw = self._ollama_chat_json(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
            )
        else:
            raise LLMError(f"Unsupported LLM provider: {self.provider}")

        try:
            return output_model.model_validate(raw)
        except Exception as exc:
            logger.error(
                "Failed to parse LLM JSON into output model",
                extra={"error": str(exc)},
            )
            raise LLMError("Failed to parse LLM output into Pydantic model") from exc

    # provider-specific internals

    def _ollama_chat_json(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
    ) -> Dict[str, Any]:
        """
        Call a local Ollama chat endpoint and expect JSON output.

        We assume a service like:
          POST $OLLAMA_BASE_URL/api/chat
          {
            "model": "llama3",
            "messages": [
              {"role": "system", "content": "..."},
              {"role": "user", "content": "..."}
            ],
            "format": "json"
          }

        The response is expected to contain:
          {"message": {"content": "<json string or object>"}}
        """
        base_url = (
            # Allow overriding via env; otherwise assume default
            "http://localhost:11434"
        )

        url = base_url.rstrip("/") + "/api/chat"

        system_msg = system_prompt or (
            "You are a strict JSON-producing assistant. "
            "You NEVER output anything except pure JSON that matches the given schema."
        )

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
            "format": "json",
            "options": {"temperature": temperature},
        }

        logger.info(
            "Calling Ollama chat for structured output",
            extra={"model": self.model},
        )

        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(url, json=payload)
        except Exception as exc:
            logger.error(
                "Ollama chat request failed",
                extra={"error": str(exc)},
            )
            raise LLMError("Ollama chat request failed") from exc

        if resp.status_code != 200:
            logger.error(
                "Ollama returned non-200 status",
                extra={"status_code": resp.status_code, "body": resp.text},
            )
            raise LLMError(f"Ollama returned status {resp.status_code}: {resp.text}")

        data = resp.json()
        message = data.get("message") or {}
        content = message.get("content")

        if isinstance(content, str):
            import json

            try:
                return json.loads(content)
            except json.JSONDecodeError as exc:
                logger.error(
                    "Failed to decode JSON from Ollama content",
                    extra={"error": str(exc), "content": content[:200]},
                )
                raise LLMError("Failed to decode JSON from Ollama content") from exc

        if isinstance(content, dict):
            return content

        logger.error(
            "Unexpected Ollama content type",
            extra={"content_type": type(content).__name__},
        )
        raise LLMError("Unexpected content format from Ollama")


@lru_cache()
def get_llm_client() -> LLMClient:
    """
    Cached LLM client instance based on settings.llm.
    """
    llm_settings = settings.llm
    logger.info(
        "Initializing LLM client",
        extra={"provider": llm_settings.provider, "model": llm_settings.model},
    )
    return LLMClient(
        provider=llm_settings.provider,
        model=llm_settings.model,
    )
