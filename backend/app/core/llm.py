from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Dict, Optional, Type, TypeVar

import httpx
from pydantic import BaseModel

from ..observability.logging import get_logger
from .config import settings

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional import at runtime
    OpenAI = None  # type: ignore[assignment]

logger = get_logger("core.llm")

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """Raised when the LLM provider returns an error or invalid response."""


class LLMClient:
    def __init__(self) -> None:
        self.cfg = settings.llm

    def generate_structured(
        self,
        prompt: str,
        output_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> T:
        raw: Dict[str, Any]
        if self.cfg.provider == "ollama":
            raw = self._generate_with_ollama(prompt, system_prompt, temperature)
        elif self.cfg.provider == "groq":
            raw = self._generate_with_groq(prompt, system_prompt, temperature)
        elif self.cfg.provider == "hybrid":
            raw = self._generate_hybrid(prompt, system_prompt, temperature)
        else:
            raise LLMError(f"Unsupported LLM provider: {self.cfg.provider}")

        try:
            return output_model.model_validate(raw)
        except Exception as exc:
            logger.error("Failed to parse LLM JSON into output model", extra={"error": str(exc)})
            raise LLMError("Failed to parse LLM output into Pydantic model") from exc

    def _strict_json_system_prompt(self, system_prompt: Optional[str]) -> str:
        if system_prompt:
            return system_prompt
        return (
            "You are a strict JSON-producing assistant. "
            "You NEVER output anything except pure JSON that matches the requested schema."
        )

    def _parse_json_content(self, content: Any, provider: str) -> Dict[str, Any]:
        if isinstance(content, dict):
            return content
        if isinstance(content, str):
            try:
                return json.loads(content)
            except json.JSONDecodeError as exc:
                raise LLMError(f"{provider} returned non-JSON content") from exc
        raise LLMError(f"{provider} returned unexpected content type: {type(content).__name__}")

    def _generate_hybrid(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
    ) -> Dict[str, Any]:
        primary = self.cfg.primary_provider
        fallback = self.cfg.fallback_provider

        try:
            if primary == "ollama":
                return self._generate_with_ollama(prompt, system_prompt, temperature)
            return self._generate_with_groq(prompt, system_prompt, temperature)
        except LLMError as exc:
            logger.error(
                "Primary LLM provider failed, attempting fallback",
                extra={"primary_provider": primary, "fallback_provider": fallback, "error": str(exc)},
            )

        if fallback == "ollama":
            return self._generate_with_ollama(prompt, system_prompt, temperature)
        return self._generate_with_groq(prompt, system_prompt, temperature)

    def _generate_with_ollama(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
    ) -> Dict[str, Any]:
        url = self.cfg.ollama_base_url.rstrip("/") + "/api/chat"
        payload: Dict[str, Any] = {
            "model": self.cfg.ollama_model or self.cfg.model,
            "messages": [
                {"role": "system", "content": self._strict_json_system_prompt(system_prompt)},
                {"role": "user", "content": prompt},
            ],
            "format": "json",
            "options": {"temperature": temperature},
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(url, json=payload)
        except Exception as exc:
            raise LLMError("Ollama chat request failed") from exc

        if resp.status_code != 200:
            raise LLMError(f"Ollama returned status {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        content = (data.get("message") or {}).get("content")
        return self._parse_json_content(content, "ollama")

    def _generate_with_groq(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
    ) -> Dict[str, Any]:
        if OpenAI is None:
            raise LLMError("openai package is not installed; cannot call Groq")
        if not self.cfg.groq_api_key:
            raise LLMError("COPILOT_GROQ_API_KEY is not set")

        client = OpenAI(
            api_key=self.cfg.groq_api_key,
            base_url=self.cfg.groq_base_url,
        )
        try:
            response = client.chat.completions.create(
                model=self.cfg.groq_model,
                temperature=temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": self._strict_json_system_prompt(system_prompt)},
                    {"role": "user", "content": prompt},
                ],
            )
        except Exception as exc:
            raise LLMError("Groq chat request failed") from exc

        if not response.choices:
            raise LLMError("Groq returned no choices")
        content = response.choices[0].message.content
        return self._parse_json_content(content, "groq")


@lru_cache()
def get_llm_client() -> LLMClient:
    llm_settings = settings.llm
    logger.info(
        "Initializing LLM client",
        extra={
            "provider": llm_settings.provider,
            "primary_provider": llm_settings.primary_provider,
            "fallback_provider": llm_settings.fallback_provider,
            "model": llm_settings.model,
        },
    )
    return LLMClient()
