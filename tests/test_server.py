"""Tests for the FastAPI REST server (taparash_pkg/server.py).

Uses FastAPI's TestClient (backed by httpx) — no live server needed.
"""

import pytest

try:
    from fastapi.testclient import TestClient
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False

skip_no_fastapi = pytest.mark.skipif(
    not _FASTAPI_AVAILABLE, reason="fastapi not installed"
)


@pytest.fixture(scope="module")
def client():
    from taparash.server import create_app
    from taparash import QualityConfig

    config = QualityConfig(
        enable_pii_masking=True,
        entropy_threshold=5.5,
        enable_fuzzy_dedup=False,
        enable_dlq=False,
    )
    app = create_app(config)
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Health / meta
# ---------------------------------------------------------------------------

@skip_no_fastapi
def test_health_returns_200(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body


@skip_no_fastapi
def test_stats_returns_200(client):
    r = client.get("/stats")
    assert r.status_code == 200
    body = r.json()
    assert "total_processed" in body
    assert "accepted" in body


# ---------------------------------------------------------------------------
# POST /filter
# ---------------------------------------------------------------------------

@skip_no_fastapi
def test_filter_accepts_valid_chunks(client):
    r = client.post("/filter", json={"texts": [
        "This is a clean and valid text chunk for the pipeline test.",
        "Another valid piece of content that should pass all gates.",
    ]})
    assert r.status_code == 200
    body = r.json()
    assert body["accepted_count"] == 2
    assert body["rejected_count"] == 0
    assert body["total"] == 2
    assert isinstance(body["acceptance_rate"], float)


@skip_no_fastapi
def test_filter_rejects_short_chunks(client):
    r = client.post("/filter", json={"texts": [
        "Too short.",
        "This text is definitely long enough to pass the minimum length gate.",
    ]})
    assert r.status_code == 200
    body = r.json()
    assert body["accepted_count"] == 1
    assert body["rejected_count"] == 1
    assert body["rejected"][0]["reason_code"] == "LENGTH_TOO_SHORT"


@skip_no_fastapi
def test_filter_masks_pii_in_accepted(client):
    r = client.post("/filter", json={"texts": [
        "Please contact info@company.com for support and assistance."
    ]})
    assert r.status_code == 200
    body = r.json()
    assert body["accepted_count"] == 1
    assert "info@company.com" not in body["accepted"][0]
    assert "[REDACTED]" in body["accepted"][0]


@skip_no_fastapi
def test_filter_deduplication(client):
    # Use a fresh app instance so dedup state is clean
    from taparash.server import create_app
    from taparash import QualityConfig

    app = create_app(QualityConfig(
        enable_exact_dedup=True,
        enable_fuzzy_dedup=False,
        enable_pii_masking=False,
        enable_dlq=False,
    ))
    with TestClient(app) as c:
        text = "Exact duplicate text for testing the dedup endpoint correctly."
        r = c.post("/filter", json={"texts": [text, text]})
        body = r.json()
        assert body["accepted_count"] == 1
        assert body["rejected_count"] == 1


@skip_no_fastapi
def test_filter_empty_batch(client):
    r = client.post("/filter", json={"texts": []})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert body["accepted_count"] == 0


@skip_no_fastapi
def test_filter_rejected_includes_reason(client):
    r = client.post("/filter", json={"texts": ["x"]})
    body = r.json()
    assert body["rejected"][0]["reason_code"] is not None
    assert body["rejected"][0]["original_text"] == "x"


# ---------------------------------------------------------------------------
# POST /filter/single
# ---------------------------------------------------------------------------

@skip_no_fastapi
def test_filter_single_valid(client):
    r = client.post("/filter/single", json={
        "text": "This is a valid chunk that should pass all quality gates."
    })
    assert r.status_code == 200
    body = r.json()
    assert body["is_valid"] is True
    assert body["reason_code"] is None


@skip_no_fastapi
def test_filter_single_rejected(client):
    r = client.post("/filter/single", json={"text": "hi"})
    assert r.status_code == 200
    body = r.json()
    assert body["is_valid"] is False
    assert body["reason_code"] == "LENGTH_TOO_SHORT"


@skip_no_fastapi
def test_filter_single_pii_masked(client):
    r = client.post("/filter/single", json={
        "text": "Reach us at admin@example.com for more information please."
    })
    body = r.json()
    assert body["is_valid"] is True
    assert "admin@example.com" not in body["text"]
    assert "[REDACTED]" in body["text"]


# ---------------------------------------------------------------------------
# POST /mask
# ---------------------------------------------------------------------------

@skip_no_fastapi
def test_mask_endpoint(client):
    r = client.post("/mask", json={"texts": [
        "Contact sales@example.com or call +1-800-555-0199 for help.",
        "No PII here at all.",
    ]})
    assert r.status_code == 200
    body = r.json()
    assert len(body["texts"]) == 2
    assert "sales@example.com" not in body["texts"][0]
    assert body["pii_hits"] >= 2


@skip_no_fastapi
def test_mask_empty_list(client):
    r = client.post("/mask", json={"texts": []})
    assert r.status_code == 200
    body = r.json()
    assert body["texts"] == []
    assert body["pii_hits"] == 0


# ---------------------------------------------------------------------------
# Stats accumulate across requests
# ---------------------------------------------------------------------------

@skip_no_fastapi
def test_stats_accumulate(client):
    from taparash.server import create_app
    from taparash import QualityConfig

    app = create_app(QualityConfig(enable_pii_masking=False, enable_dlq=False))
    with TestClient(app) as c:
        c.post("/filter", json={"texts": [
            "Valid first chunk for stats accumulation test.",
            "Valid second chunk for stats accumulation test.",
        ]})
        r = c.get("/stats")
        body = r.json()
        assert body["total_processed"] == 2


# ---------------------------------------------------------------------------
# create_app raises without fastapi
# ---------------------------------------------------------------------------

def test_create_app_importable():
    from taparash.server import create_app
    assert create_app is not None
