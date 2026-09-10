"""Tests for the Prometheus metrics exporter."""

import pytest

try:
    from prometheus_client import CollectorRegistry, generate_latest
    _PROM_AVAILABLE = True
except ImportError:
    _PROM_AVAILABLE = False

skip_no_prom = pytest.mark.skipif(
    not _PROM_AVAILABLE, reason="prometheus-client not installed"
)


def make_filter(**kw):
    from taparash import TaparashFilter, QualityConfig
    return TaparashFilter(QualityConfig(enable_dlq=False, **kw))


def make_collector(pipeline=None, prefix="taparash"):
    from taparash.metrics_exporter import TaparashCollector
    registry = CollectorRegistry()
    if pipeline is None:
        pipeline = make_filter()
    TaparashCollector(pipeline, prefix=prefix, registry=registry)
    return registry


def scrape(registry) -> str:
    return generate_latest(registry).decode("utf-8")


# ---------------------------------------------------------------------------
# Import / instantiation
# ---------------------------------------------------------------------------

def test_collector_importable():
    from taparash.metrics_exporter import TaparashCollector
    assert TaparashCollector is not None


def test_collector_raises_without_prometheus():
    try:
        import prometheus_client  # noqa: F401
        pytest.skip("prometheus-client is installed")
    except ImportError:
        pass
    from taparash.metrics_exporter import TaparashCollector
    with pytest.raises(ImportError, match="prometheus-client"):
        TaparashCollector(make_filter())


# ---------------------------------------------------------------------------
# Metric names present in output
# ---------------------------------------------------------------------------

@skip_no_prom
def test_all_metric_families_present():
    registry = make_collector()
    output = scrape(registry)
    assert "taparash_chunks_processed_total" in output
    assert "taparash_chunks_accepted_total" in output
    assert "taparash_chunks_rejected_total" in output
    assert "taparash_acceptance_rate" in output
    assert "taparash_pipeline_info" in output


@skip_no_prom
def test_rejection_reason_labels_present():
    registry = make_collector()
    output = scrape(registry)
    for reason in ("length", "entropy", "exact_duplicate",
                   "fuzzy_duplicate", "semantic_duplicate", "contradiction"):
        assert f'reason="{reason}"' in output


@skip_no_prom
def test_pipeline_info_contains_version():
    registry = make_collector()
    output = scrape(registry)
    assert 'version="' in output


# ---------------------------------------------------------------------------
# Values reflect pipeline stats
# ---------------------------------------------------------------------------

@skip_no_prom
def test_zero_stats_before_processing():
    registry = make_collector()
    output = scrape(registry)
    assert 'taparash_chunks_processed_total 0.0' in output
    assert 'taparash_chunks_accepted_total 0.0' in output


@skip_no_prom
def test_stats_reflect_accepted_chunks():
    f = make_filter(enable_pii_masking=False, enable_fuzzy_dedup=False)
    registry = make_collector(f)

    texts = [
        "First valid chunk for Prometheus metric verification test.",
        "Second valid chunk for Prometheus metric verification test.",
    ]
    for t in texts:
        f.process_single(t)

    output = scrape(registry)
    assert "taparash_chunks_processed_total 2.0" in output
    assert "taparash_chunks_accepted_total 2.0" in output


@skip_no_prom
def test_stats_reflect_rejected_chunks():
    f = make_filter(min_chunk_length=100)
    registry = make_collector(f)

    f.process_single("too short")  # rejected — below min_chunk_length=100
    # 110 chars — passes length gate
    f.process_single("A" * 110)

    output = scrape(registry)
    assert 'reason="length"} 1.0' in output


@skip_no_prom
def test_acceptance_rate_zero_with_no_data():
    registry = make_collector()
    output = scrape(registry)
    assert "taparash_acceptance_rate 0.0" in output


@skip_no_prom
def test_acceptance_rate_one_all_accepted():
    f = make_filter(enable_pii_masking=False, enable_fuzzy_dedup=False)
    registry = make_collector(f)

    f.process_single("Valid text chunk that passes all quality gates easily.")
    output = scrape(registry)
    assert "taparash_acceptance_rate 1.0" in output


# ---------------------------------------------------------------------------
# Custom prefix
# ---------------------------------------------------------------------------

@skip_no_prom
def test_custom_prefix():
    from taparash.metrics_exporter import TaparashCollector
    f = make_filter()
    registry = CollectorRegistry()
    TaparashCollector(f, prefix="myapp", registry=registry)
    output = scrape(registry)
    assert "myapp_chunks_processed_total" in output
    assert "taparash_" not in output


# ---------------------------------------------------------------------------
# Multiple scrapes return fresh data (pull model)
# ---------------------------------------------------------------------------

@skip_no_prom
def test_metrics_update_across_scrapes():
    f = make_filter(enable_pii_masking=False, enable_fuzzy_dedup=False)
    registry = make_collector(f)

    output_before = scrape(registry)
    assert "taparash_chunks_processed_total 0.0" in output_before

    f.process_single("A valid text chunk for the scrape update test here.")
    output_after = scrape(registry)
    assert "taparash_chunks_processed_total 1.0" in output_after


# ---------------------------------------------------------------------------
# /metrics endpoint on the REST server
# ---------------------------------------------------------------------------

@skip_no_prom
def test_server_metrics_endpoint():
    from fastapi.testclient import TestClient
    from taparash.server import create_app
    from taparash import QualityConfig

    app = create_app(QualityConfig(enable_pii_masking=False, enable_dlq=False))
    with TestClient(app) as client:
        # Process something so there are non-zero stats
        client.post("/filter", json={"texts": [
            "A valid text chunk processed before Prometheus scrape."
        ]})
        r = client.get("/metrics")

    assert r.status_code == 200
    assert "taparash_chunks_processed_total" in r.text
    assert "taparash_chunks_accepted_total" in r.text
    assert "taparash_acceptance_rate" in r.text


@skip_no_prom
def test_server_metrics_content_type():
    from fastapi.testclient import TestClient
    from taparash.server import create_app
    from taparash import QualityConfig

    app = create_app(QualityConfig(enable_dlq=False))
    with TestClient(app) as client:
        r = client.get("/metrics")

    assert "text/plain" in r.headers["content-type"]
