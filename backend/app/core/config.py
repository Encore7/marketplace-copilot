from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application configuration.

    Values are loaded from environment variables and the .env file.
    """

    # App
    app_name: str = "Marketplace Seller Intelligence Copilot"
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # Logging
    log_level: str = "INFO"

    # OpenTelemetry / Tracing
    otel_service_name: str = "marketplace-copilot-api"
    otel_exporter_otlp_endpoint: str = "http://alloy:4317"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
