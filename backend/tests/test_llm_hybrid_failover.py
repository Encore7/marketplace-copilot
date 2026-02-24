from types import SimpleNamespace

from pydantic import BaseModel

from backend.app.core.llm import LLMClient, LLMError


class _Out(BaseModel):
    value: int


def test_hybrid_falls_back_when_primary_fails(monkeypatch):
    client = LLMClient()
    client.cfg = SimpleNamespace(
        provider="hybrid",
        primary_provider="ollama",
        fallback_provider="groq",
        ollama_base_url="http://localhost:11434",
        ollama_model="qwen3:14b",
        groq_api_key="dummy",
        groq_base_url="https://api.groq.com/openai/v1",
        groq_model="llama-3.3-70b-versatile",
        model="qwen3:14b",
    )

    def _raise_ollama(*args, **kwargs):
        raise LLMError("boom")

    monkeypatch.setattr(
        client,
        "_generate_with_ollama",
        _raise_ollama,
    )
    monkeypatch.setattr(
        client,
        "_generate_with_groq",
        lambda prompt, system_prompt, temperature: {"value": 42},
    )

    out = client.generate_structured("test", _Out)
    assert out.value == 42
