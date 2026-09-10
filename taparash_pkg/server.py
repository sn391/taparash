"""FastAPI REST server for Taparash.

Start via CLI:
    taparash serve [--host 0.0.0.0] [--port 8000] [--config pipeline.toml]

Or programmatically:
    import uvicorn
    from taparash.server import create_app
    from taparash import QualityConfig

    app = create_app(QualityConfig(enable_dlq=False))
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""

from __future__ import annotations

import os
from typing import List, Optional

try:
    from fastapi import FastAPI
    from pydantic import BaseModel as _BaseModel
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False
    FastAPI = None  # type: ignore[assignment,misc]
    _BaseModel = object  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class FilterRequest(_BaseModel):  # type: ignore[misc]
    texts: List[str]


class RejectedChunk(_BaseModel):  # type: ignore[misc]
    original_text: str
    text: str
    reason_code: Optional[str] = None


class FilterResponse(_BaseModel):  # type: ignore[misc]
    accepted: List[str]
    rejected: List[RejectedChunk]
    total: int
    accepted_count: int
    rejected_count: int
    acceptance_rate: float


class SingleFilterRequest(_BaseModel):  # type: ignore[misc]
    text: str


class SingleFilterResponse(_BaseModel):  # type: ignore[misc]
    text: str
    is_valid: bool
    reason_code: Optional[str] = None


class MaskRequest(_BaseModel):  # type: ignore[misc]
    texts: List[str]


class MaskResponse(_BaseModel):  # type: ignore[misc]
    texts: List[str]
    pii_hits: int


class HealthResponse(_BaseModel):  # type: ignore[misc]
    status: str
    version: str


class StatsResponse(_BaseModel):  # type: ignore[misc]
    total_processed: int
    accepted: int
    rejected_length: int
    rejected_entropy: int
    rejected_exact_duplicate: int
    rejected_fuzzy_duplicate: int
    rejected_semantic_duplicate: int
    rejected_contradiction: int


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app(config=None) -> "FastAPI":
    """Create and return a configured FastAPI application.

    Args:
        config: ``QualityConfig`` to use for all requests.
                Defaults to ``QualityConfig(enable_dlq=False)``.

    Returns:
        A ``FastAPI`` application instance.

    Raises:
        ImportError: If ``fastapi`` is not installed.
    """
    if not _FASTAPI_AVAILABLE:
        raise ImportError(
            "FastAPI is required to run the REST server. "
            "Install it with: pip install taparash[api]"
        )

    try:
        from taparash.config import QualityConfig
        from taparash.pipeline import TaparashFilter
        from taparash.core.pii import PIIMasker
        from taparash import __version__
    except ImportError:
        from config import QualityConfig  # type: ignore[no-redef]
        from pipeline import TaparashFilter  # type: ignore[no-redef]
        from core.pii import PIIMasker  # type: ignore[no-redef]
        __version__ = "unknown"

    _config = config or QualityConfig(enable_dlq=False)
    _filter = TaparashFilter(_config)
    _masker = PIIMasker(
        mask_emails=_config.pii_mask_emails,
        mask_phones=_config.pii_mask_phones,
        mask_credit_cards=_config.pii_mask_credit_cards,
        mask_ssn=_config.pii_mask_ssn,
        mask_iban=_config.pii_mask_iban,
        mask_eu_vat=_config.pii_mask_eu_vat,
        mask_eu_phone=_config.pii_mask_eu_phone,
        replacement_token=_config.pii_replacement_token,
    )

    app = FastAPI(
        title="Taparash API",
        description=(
            "Zero-LLM data quality & compliance gateway for RAG systems. "
            "Offline PII masking, deduplication, and entropy filtering."
        ),
        version=__version__,
    )

    # ---- Prometheus /metrics -----------------------------------------------
    try:
        from prometheus_client import CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
        from taparash.metrics_exporter import TaparashCollector
        from fastapi import Response as _Response

        _prom_registry = CollectorRegistry()
        TaparashCollector(_filter, registry=_prom_registry)

        @app.get("/metrics", include_in_schema=False, tags=["meta"])
        async def prometheus_metrics():
            """Prometheus text-format metrics — scrape with ``prometheus.yml``."""
            return _Response(
                content=generate_latest(_prom_registry),
                media_type=CONTENT_TYPE_LATEST,
            )

    except ImportError:

        @app.get("/metrics", include_in_schema=False, tags=["meta"])
        async def prometheus_metrics_unavailable():  # type: ignore[misc]
            from fastapi import Response as _Response
            return _Response(
                content="# prometheus-client not installed: pip install taparash[metrics]\n",
                media_type="text/plain",
                status_code=503,
            )

    # ---- Health / meta -----------------------------------------------------

    @app.get("/health", response_model=HealthResponse, tags=["meta"])
    async def health():
        """Liveness probe — always returns 200 when the server is up."""
        return HealthResponse(status="ok", version=__version__)

    @app.get("/stats", response_model=StatsResponse, tags=["meta"])
    async def stats():
        """Cumulative pipeline statistics since server start."""
        s = _filter.stats
        return StatsResponse(
            total_processed=s["total_processed"],
            accepted=s["accepted"],
            rejected_length=s["rejected_length"],
            rejected_entropy=s["rejected_entropy"],
            rejected_exact_duplicate=s["rejected_exact_duplicate"],
            rejected_fuzzy_duplicate=s["rejected_fuzzy_duplicate"],
            rejected_semantic_duplicate=s["rejected_semantic_duplicate"],
            rejected_contradiction=s["rejected_contradiction"],
        )

    # ---- Filter endpoints --------------------------------------------------

    @app.post("/filter", response_model=FilterResponse, tags=["filter"])
    async def filter_batch(req: FilterRequest):
        """Filter a batch of text chunks through all quality gates.

        Accepted chunks are returned with PII masked (if enabled).
        Rejected chunks include the rejection reason code.
        """
        result = await _filter.aprocess_batch(req.texts)
        return FilterResponse(
            accepted=[r.text for r in result.accepted],
            rejected=[
                RejectedChunk(
                    original_text=r.original_text,
                    text=r.text,
                    reason_code=r.reason_code,
                )
                for r in result.rejected
            ],
            total=result.total,
            accepted_count=len(result.accepted),
            rejected_count=len(result.rejected),
            acceptance_rate=result.acceptance_rate,
        )

    @app.post("/filter/single", response_model=SingleFilterResponse, tags=["filter"])
    async def filter_single(req: SingleFilterRequest):
        """Filter a single text chunk through all quality gates."""
        result = await _filter.aprocess_single(req.text)
        return SingleFilterResponse(
            text=result.text,
            is_valid=result.is_valid,
            reason_code=result.reason_code,
        )

    # ---- PII masking -------------------------------------------------------

    @app.post("/mask", response_model=MaskResponse, tags=["pii"])
    async def mask(req: MaskRequest):
        """Apply PII masking only — no dedup, entropy, or length filtering."""
        masked_texts = []
        total_hits = 0
        for text in req.texts:
            masked, matches = _masker.mask(text)
            masked_texts.append(masked)
            total_hits += len(matches)
        return MaskResponse(texts=masked_texts, pii_hits=total_hits)

    return app


# ---------------------------------------------------------------------------
# Default app instance  (used by: uvicorn taparash.server:app)
# ---------------------------------------------------------------------------

def _build_default_app() -> "FastAPI":
    config_path = os.environ.get("TAPARASH_CONFIG")
    if config_path:
        try:
            from taparash.config_io import load_config
            config = load_config(config_path)
        except Exception:
            from taparash.config import QualityConfig
            config = QualityConfig(enable_dlq=False)
    else:
        try:
            from taparash.config import QualityConfig
        except ImportError:
            from config import QualityConfig  # type: ignore[no-redef]
        config = QualityConfig(enable_dlq=False)
    return create_app(config)


if _FASTAPI_AVAILABLE:
    app = _build_default_app()
