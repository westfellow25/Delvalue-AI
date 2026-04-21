"""
DelValue AI — Telemetry & Observability

Structured logging, request tracking, and metrics.
"""

from __future__ import annotations

import logging
import sys
import time
from collections import defaultdict
from threading import Lock
from typing import Optional

import structlog

from api.config import get_settings

settings = get_settings()


def configure_logging() -> None:
    """Configure structlog for structured JSON logging."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        stream=sys.stdout,
        format="%(message)s",
    )

    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.environment.value == "development":
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


class MetricsCollector:
    """Simple in-memory metrics (counters, histograms). Swap for Prometheus in prod."""

    def __init__(self):
        self._counters: dict[str, float] = defaultdict(float)
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._gauges: dict[str, float] = {}
        self._lock = Lock()

    def increment(self, name: str, value: float = 1.0, labels: Optional[dict] = None) -> None:
        key = self._key(name, labels)
        with self._lock:
            self._counters[key] += value

    def observe(self, name: str, value: float, labels: Optional[dict] = None) -> None:
        key = self._key(name, labels)
        with self._lock:
            self._histograms[key].append(value)
            if len(self._histograms[key]) > 10_000:
                self._histograms[key] = self._histograms[key][-5000:]

    def gauge(self, name: str, value: float, labels: Optional[dict] = None) -> None:
        key = self._key(name, labels)
        with self._lock:
            self._gauges[key] = value

    def snapshot(self) -> dict:
        with self._lock:
            import numpy as np
            histogram_stats = {}
            for name, values in self._histograms.items():
                if values:
                    histogram_stats[name] = {
                        "count": len(values),
                        "mean": float(np.mean(values)),
                        "p50": float(np.percentile(values, 50)),
                        "p95": float(np.percentile(values, 95)),
                        "p99": float(np.percentile(values, 99)),
                    }
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": histogram_stats,
            }

    @staticmethod
    def _key(name: str, labels: Optional[dict]) -> str:
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"


_metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    return _metrics


class Timer:
    """Context manager for timing operations."""

    def __init__(self, metric_name: str, labels: Optional[dict] = None):
        self.metric_name = metric_name
        self.labels = labels
        self.start_time = 0.0
        self.elapsed_ms = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed_ms = (time.perf_counter() - self.start_time) * 1000
        _metrics.observe(self.metric_name, self.elapsed_ms, labels=self.labels)
