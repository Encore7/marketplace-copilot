from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class AppEnv(str, Enum):
    LOCAL = "local"
    DEV = "dev"
    PROD = "prod"


class AppSettings(BaseModel):
    name: str = Field(default="Marketplace Seller Intelligence Copilot")
    env: AppEnv = Field(default=AppEnv.DEV)
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO"
    )

    @field_validator("port")
    @classmethod
    def validate_port(cls, value: int) -> int:
        if not (1 <= value <= 65535):
            raise ValueError("APP_PORT must be between 1 and 65535")
        return value


class OTELSettings(BaseModel):
    service_name: str = Field(default="marketplace-copilot-api")
    exporter_otlp_endpoint: str = Field(default="http://alloy:4317")
    exporter_otlp_protocol: Literal["grpc", "http/protobuf", "http/json"] = Field(
        default="grpc"
    )


class WarehouseSettings(BaseModel):
    """
    Seller "warehouse" connection.

    For now this is a DuckDB DSN like:
      duckdb:///app_storage/seller_warehouse.duckdb
    We can switch to Postgres/Snowflake/etc. by changing this DSN
    and the repository implementation.
    """

    seller_warehouse_dsn: str = Field(
        default="duckdb:///app_storage/seller_warehouse.duckdb"
    )
    seller_data_root: str = Field(default="data/seller")


class RAGSettings(BaseModel):
    backend: Literal["opensearch", "local_file"] = Field(default="opensearch")
    vector_store_url: str = Field(default="http://rag-vector-store:8000")
    vector_store_collection: str = Field(default="marketplace_policies")
    opensearch_url: str = Field(default="http://localhost:9200")
    opensearch_index: str = Field(default="marketplace_policies")
    opensearch_timeout_seconds: float = Field(default=10.0)


class LLMSettings(BaseModel):
    provider: Literal["hybrid", "ollama", "groq"] = Field(default="hybrid")
    model: str = Field(default="qwen3:14b")
    primary_provider: Literal["ollama", "groq"] = Field(default="ollama")
    fallback_provider: Literal["ollama", "groq"] = Field(default="groq")
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="qwen3:14b")
    groq_api_key: Optional[str] = None
    groq_base_url: str = Field(default="https://api.groq.com/openai/v1")
    groq_model: str = Field(default="llama-3.3-70b-versatile")
    embed_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")


class LLMObservabilitySettings(BaseModel):
    tracing_v2: bool = False
    langsmith_api_key: Optional[str] = None
    langsmith_project: Optional[str] = "marketplace-copilot"


class PromptVersionSettings(BaseModel):
    planner: str = Field(default="v1")
    critic: str = Field(default="v1")
    final_answer: str = Field(default="v1")
    listing_agent: str = Field(default="v1")
    pricing_agent: str = Field(default="v1")
    compliance_agent: str = Field(default="v1")
    inventory_agent: str = Field(default="v1")
    profit_agent: str = Field(default="v1")


class Settings(BaseSettings):
    """
    Top-level application settings loaded from environment.

    Priority:
      1. COPILOT_* variables (new, namespaced)
      2. Legacy APP_* / OTEL_* where appropriate
    """

    # App
    app_name: Optional[str] = None
    app_env: Optional[str] = None
    app_host: Optional[str] = None
    app_port: Optional[int] = None
    log_level: Optional[str] = None

    # OTEL
    otel_service_name: Optional[str] = None
    otel_exporter_otlp_endpoint: Optional[str] = None
    otel_exporter_otlp_protocol: Optional[str] = None

    # Warehouse
    seller_warehouse_dsn: Optional[str] = None
    seller_data_root: Optional[str] = None

    # RAG
    rag_vector_store_url: Optional[str] = None
    rag_vector_store_collection: Optional[str] = None
    rag_backend: Optional[str] = None
    opensearch_url: Optional[str] = None
    opensearch_index: Optional[str] = None
    opensearch_timeout_seconds: Optional[float] = None

    # LLM
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_primary_provider: Optional[str] = None
    llm_fallback_provider: Optional[str] = None
    ollama_base_url: Optional[str] = None
    ollama_model: Optional[str] = None
    groq_api_key: Optional[str] = None
    groq_base_url: Optional[str] = None
    groq_model: Optional[str] = None
    embed_model: Optional[str] = None

    # LLM Observability
    langchain_tracing_v2: Optional[str] = None
    langchain_api_key: Optional[str] = None
    langchain_project: Optional[str] = None
    langsmith_api_key: Optional[str] = None
    langsmith_project: Optional[str] = None

    # Prompts
    planner_prompt_version: Optional[str] = None
    critic_prompt_version: Optional[str] = None
    final_answer_prompt_version: Optional[str] = None
    listing_agent_prompt_version: Optional[str] = None
    pricing_agent_prompt_version: Optional[str] = None
    compliance_agent_prompt_version: Optional[str] = None
    inventory_agent_prompt_version: Optional[str] = None
    profit_agent_prompt_version: Optional[str] = None

    class Config:
        env_prefix = "COPILOT_"
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def app(self) -> AppSettings:
        name = self.app_name or self._get_legacy("APP_NAME") or AppSettings().name
        env_str = self.app_env or self._get_legacy("APP_ENV") or AppSettings().env
        host = self.app_host or self._get_legacy("APP_HOST") or AppSettings().host
        port = self.app_port or int(self._get_legacy("APP_PORT", "8000"))
        log_level = (
            self.log_level or self._get_legacy("LOG_LEVEL") or AppSettings().log_level
        )

        return AppSettings(
            name=name,
            env=AppEnv(env_str),
            host=host,
            port=port,
            log_level=log_level,  # validated by AppSettings
        )

    @property
    def otel(self) -> OTELSettings:
        service_name = (
            self.otel_service_name
            or self._get_legacy("OTEL_SERVICE_NAME")
            or OTELSettings().service_name
        )
        endpoint = (
            self.otel_exporter_otlp_endpoint
            or self._get_legacy("OTEL_EXPORTER_OTLP_ENDPOINT")
            or OTELSettings().exporter_otlp_endpoint
        )
        protocol = (
            self.otel_exporter_otlp_protocol
            or self._get_legacy("OTEL_EXPORTER_OTLP_PROTOCOL")
            or OTELSettings().exporter_otlp_protocol
        )

        return OTELSettings(
            service_name=service_name,
            exporter_otlp_endpoint=endpoint,
            exporter_otlp_protocol=protocol,
        )

    @property
    def warehouse(self) -> WarehouseSettings:
        dsn = (
            self.seller_warehouse_dsn
            or self._get_legacy("COPILOT_SELLER_WAREHOUSE_DSN")
            or WarehouseSettings().seller_warehouse_dsn
        )
        data_root = (
            self.seller_data_root
            or
            self._get_legacy("COPILOT_SELLER_DATA_ROOT")
            or WarehouseSettings().seller_data_root
        )
        return WarehouseSettings(
            seller_warehouse_dsn=dsn,
            seller_data_root=data_root,
        )

    @property
    def rag(self) -> RAGSettings:
        url = self.rag_vector_store_url or RAGSettings().vector_store_url
        collection = (
            self.rag_vector_store_collection or RAGSettings().vector_store_collection
        )
        backend = self.rag_backend or RAGSettings().backend
        opensearch_url = self.opensearch_url or RAGSettings().opensearch_url
        opensearch_index = self.opensearch_index or RAGSettings().opensearch_index
        opensearch_timeout_seconds = (
            self.opensearch_timeout_seconds or RAGSettings().opensearch_timeout_seconds
        )
        return RAGSettings(
            backend=backend,
            vector_store_url=url,
            vector_store_collection=collection,
            opensearch_url=opensearch_url,
            opensearch_index=opensearch_index,
            opensearch_timeout_seconds=opensearch_timeout_seconds,
        )

    @property
    def llm(self) -> LLMSettings:
        return LLMSettings(
            provider=self.llm_provider or LLMSettings().provider,
            model=self.llm_model or LLMSettings().model,
            primary_provider=self.llm_primary_provider
            or LLMSettings().primary_provider,
            fallback_provider=self.llm_fallback_provider
            or LLMSettings().fallback_provider,
            ollama_base_url=self.ollama_base_url or LLMSettings().ollama_base_url,
            ollama_model=self.ollama_model or LLMSettings().ollama_model,
            groq_api_key=self.groq_api_key
            or self._get_legacy("GROQ_API_KEY")
            or LLMSettings().groq_api_key,
            groq_base_url=self.groq_base_url or LLMSettings().groq_base_url,
            groq_model=self.groq_model or LLMSettings().groq_model,
            embed_model=self.embed_model or LLMSettings().embed_model,
        )

    @property
    def llm_obs(self) -> LLMObservabilitySettings:
        tracing_raw = self.langchain_tracing_v2 or self._get_legacy(
            "LANGCHAIN_TRACING_V2", "false"
        )
        tracing_v2 = str(tracing_raw).strip().lower() in ("1", "true", "yes", "on")

        return LLMObservabilitySettings(
            tracing_v2=tracing_v2,
            langsmith_api_key=self.langsmith_api_key
            or self.langchain_api_key
            or self._get_legacy("LANGCHAIN_API_KEY"),
            langsmith_project=self.langsmith_project
            or self.langchain_project
            or self._get_legacy("LANGCHAIN_PROJECT")
            or LLMObservabilitySettings().langsmith_project,
        )

    @property
    def prompts(self) -> PromptVersionSettings:
        return PromptVersionSettings(
            planner=self.planner_prompt_version or PromptVersionSettings().planner,
            critic=self.critic_prompt_version or PromptVersionSettings().critic,
            final_answer=self.final_answer_prompt_version
            or PromptVersionSettings().final_answer,
            listing_agent=self.listing_agent_prompt_version
            or PromptVersionSettings().listing_agent,
            pricing_agent=self.pricing_agent_prompt_version
            or PromptVersionSettings().pricing_agent,
            compliance_agent=self.compliance_agent_prompt_version
            or PromptVersionSettings().compliance_agent,
            inventory_agent=self.inventory_agent_prompt_version
            or PromptVersionSettings().inventory_agent,
            profit_agent=self.profit_agent_prompt_version
            or PromptVersionSettings().profit_agent,
        )

    # Helpers

    @staticmethod
    def _get_legacy(name: str, default: Optional[str] = None) -> Optional[str]:
        """Read legacy env vars (APP_*, OTEL_*) directly if needed."""
        import os

        return os.getenv(name, default)


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings instance to avoid re-parsing env on every import.

    Usage:
        from backend.app.core.config import get_settings
        settings = get_settings()
        settings.app.name, settings.app.port, ...
    """
    return Settings()


settings = get_settings()
