"""Prometheus metrics exporter for Taparash.

Provides a ``TaparashCollector`` that reads live pipeline statistics from a
``TaparashFilter`` instance and exposes them as Prometheus metrics.

Usage — standalone (any WSGI/ASGI app)::

    from prometheus_client import CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
    from taparash.metrics_exporter import TaparashCollector

    registry = CollectorRegistry()
    collector = TaparashCollector(pipeline, registry=registry)

    # In your /metrics route:
    return Response(generate_latest(registry), content_type=CONTENT_TYPE_LATEST)

Usage — REST server (automatic when prometheus-client is installed)::

    taparash serve --config pipeline.toml
    # → GET /metrics  is available automatically

Exported metrics
----------------
taparash_chunks_processed_total    Counter  Total chunks seen by the pipeline.
taparash_chunks_accepted_total     Counter  Chunks that passed all gates.
taparash_chunks_rejected_total     Counter  Rejected chunks, labelled by ``reason``.
taparash_acceptance_rate           Gauge    Fraction accepted (0.0–1.0).
taparash_pipeline_info             Gauge    Static label set: version, python version.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

try:
    from prometheus_client import CollectorRegistry, REGISTRY
    from prometheus_client.core import (
        CounterMetricFamily,
        GaugeMetricFamily,
        InfoMetricFamily,
    )
    _PROMETHEUS_AVAILABLE = True
except ImportError:
    _PROMETHEUS_AVAILABLE = False
    CollectorRegistry = None  # type: ignore[assignment,misc]
    REGISTRY = None  # type: ignore[assignment]

if TYPE_CHECKING:
    pass

_REJECTION_LABELS = [
    ("length",             "rejected_length"),
    ("entropy",            "rejected_entropy"),
    ("exact_duplicate",    "rejected_exact_duplicate"),
    ("fuzzy_duplicate",    "rejected_fuzzy_duplicate"),
    ("semantic_duplicate", "rejected_semantic_duplicate"),
    ("contradiction",      "rejected_contradiction"),
]


class TaparashCollector:
    """Prometheus ``Collector`` that reads stats from a ``TaparashFilter``.

    Uses a *pull* model: metrics are generated on demand when Prometheus scrapes
    the ``/metrics`` endpoint.  No callback wiring required.

    Args:
        pipeline: A ``TaparashFilter`` instance whose ``.stats`` dict is read
                  on every scrape.
        prefix:   Metric name prefix (default: ``"taparash"``).
        registry: Prometheus ``CollectorRegistry`` to register with.
                  Pass ``None`` to skip auto-registration (useful in tests).
                  Defaults to a fresh per-instance registry.

    Raises:
        ImportError: If ``prometheus-client`` is not installed.
    """

    def __init__(
        self,
        pipeline,
        prefix: str = "taparash",
        registry: Optional["CollectorRegistry"] = None,
    ) -> None:
        if not _PROMETHEUS_AVAILABLE:
            raise ImportError(
                "prometheus-client is required for TaparashCollector. "
                "Install it with: pip install taparash[metrics]"
            )
        self._pipeline = pipeline
        self._prefix = prefix
        if registry is not None:
            registry.register(self)

    def describe(self):
        # Required by prometheus_client — return empty to avoid duplicate
        # descriptor conflicts when the same collector is re-used across tests.
        return []

    def collect(self):
        """Yield current metric families on every Prometheus scrape."""
        s = self._pipeline.stats
        p = self._prefix

        # --- total processed ------------------------------------------------
        c = CounterMetricFamily(
            f"{p}_chunks_processed_total",
            "Total text chunks seen by the Taparash pipeline.",
        )
        c.add_metric([], float(s["total_processed"]))
        yield c

        # --- accepted -------------------------------------------------------
        c = CounterMetricFamily(
            f"{p}_chunks_accepted_total",
            "Chunks that passed all quality gates.",
        )
        c.add_metric([], float(s["accepted"]))
        yield c

        # --- rejected by reason (labelled) ----------------------------------
        c = CounterMetricFamily(
            f"{p}_chunks_rejected_total",
            "Chunks rejected by the pipeline, labelled by rejection reason.",
            labels=["reason"],
        )
        for label, key in _REJECTION_LABELS:
            c.add_metric([label], float(s.get(key, 0)))
        yield c

        # --- acceptance rate ------------------------------------------------
        total = s["total_processed"]
        rate = s["accepted"] / total if total > 0 else 0.0
        g = GaugeMetricFamily(
            f"{p}_acceptance_rate",
            "Fraction of processed chunks that were accepted (0.0–1.0).",
        )
        g.add_metric([], rate)
        yield g

        # --- pipeline info (static labels) ----------------------------------
        import sys

        try:
            from taparash import __version__
        except ImportError:
            __version__ = "unknown"

        info = InfoMetricFamily(
            f"{p}_pipeline",
            "Static information about the running Taparash pipeline.",
        )
        info.add_metric(
            [],
            {
                "version": __version__,
                "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            },
        )
        yield info
