from __future__ import annotations

from prometheus_client import Counter, Histogram

copilot_requests_total = Counter(
    "copilot_requests_total",
    "Total copilot analyze requests",
    ["mode"],
)

copilot_request_latency_seconds = Histogram(
    "copilot_request_latency_seconds",
    "Latency of copilot analyze requests in seconds",
    ["mode"],
)
