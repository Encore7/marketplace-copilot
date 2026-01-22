from __future__ import annotations

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from ..core.config import settings


def init_otel(app: FastAPI) -> None:
    """
    Initialize OpenTelemetry tracing.

    Traces are exported via OTLP gRPC to Grafana Alloy,
    which then forwards them to Tempo.
    """
    resource = Resource(
        attributes={
            "service.name": settings.otel.service_name,
            "service.environment": settings.app.env,
        }
    )

    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    span_exporter = OTLPSpanExporter(
        endpoint=settings.otel.exporter_otlp_endpoint,
        insecure=True,
    )

    span_processor = BatchSpanProcessor(span_exporter)
    tracer_provider.add_span_processor(span_processor)

    # Instrument FastAPI + Uvicorn
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
