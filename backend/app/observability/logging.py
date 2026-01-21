from __future__ import annotations

import logging
import sys
from typing import Any, Dict, Optional

from opentelemetry.trace import get_current_span

from .config import settings


class JsonFormatter(logging.Formatter):
    """
    JSON-line formatter.

    trace_id and span_id are injected via the custom log record factory.
    """

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        log_record: Dict[str, Any] = {
            "level": record.levelname,
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "logger": record.name,
            "message": record.getMessage(),
        }

        trace_id = getattr(record, "trace_id", None)
        span_id = getattr(record, "span_id", None)

        if trace_id is not None:
            log_record["trace_id"] = trace_id
        if span_id is not None:
            log_record["span_id"] = span_id

        return self._to_json_line(log_record)

    @staticmethod
    def _to_json_line(payload: Dict[str, Any]) -> str:
        import json

        return json.dumps(payload, separators=(",", ":"))


def _install_log_record_factory() -> None:
    """
    Install a log record factory that enriches log records with OTel trace/span IDs.
    """
    old_factory = logging.getLogRecordFactory()

    def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record: logging.LogRecord = old_factory(*args, **kwargs)  # type: ignore[assignment]

        span = get_current_span()
        ctx = span.get_span_context() if span is not None else None

        if ctx is not None and ctx.is_valid:
            record.trace_id = f"{ctx.trace_id:032x}"
            record.span_id = f"{ctx.span_id:016x}"
        else:
            record.trace_id = None
            record.span_id = None

        return record

    logging.setLogRecordFactory(record_factory)


def setup_logging(level: Optional[str] = None) -> None:
    """
    Configure root logger for JSON logs to stdout and install trace/span enrichment.
    """
    log_level = (level or settings.log_level).upper()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers = [handler]
    root.propagate = False

    _install_log_record_factory()
