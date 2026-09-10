"""Tests for the async pipeline API (aprocess_single / aprocess_batch).

All tests use asyncio.run() so no pytest-asyncio dependency is needed.
"""

import asyncio
import pytest
from taparash import TaparashFilter, QualityConfig


def cfg(**kw):
    return QualityConfig(enable_dlq=False, enable_pii_masking=False, **kw)


# ---------------------------------------------------------------------------
# aprocess_single
# ---------------------------------------------------------------------------

def test_aprocess_single_returns_filter_result():
    from taparash.config import FilterResult

    f = TaparashFilter(cfg())
    result = asyncio.run(
        f.aprocess_single("This is a valid text chunk for async processing test.")
    )
    assert isinstance(result, FilterResult)
    assert result.is_valid


def test_aprocess_single_rejects_short_text():
    f = TaparashFilter(cfg(min_chunk_length=100))
    result = asyncio.run(f.aprocess_single("Too short."))
    assert not result.is_valid
    assert result.reason_code == "LENGTH_TOO_SHORT"


def test_aprocess_single_matches_sync():
    f_sync = TaparashFilter(cfg(enable_exact_dedup=False, enable_fuzzy_dedup=False))
    f_async = TaparashFilter(cfg(enable_exact_dedup=False, enable_fuzzy_dedup=False))

    text = "Consistent result between sync and async processing paths here."
    sync_result = f_sync.process_single(text)
    async_result = asyncio.run(f_async.aprocess_single(text))

    assert sync_result.is_valid == async_result.is_valid
    assert sync_result.text == async_result.text
    assert sync_result.reason_code == async_result.reason_code


def test_aprocess_single_updates_stats():
    f = TaparashFilter(cfg())
    asyncio.run(f.aprocess_single("Valid text chunk for stats tracking test."))
    assert f.stats["total_processed"] == 1


def test_aprocess_single_dedup_accumulates_across_awaits():
    f = TaparashFilter(cfg(enable_exact_dedup=True, enable_fuzzy_dedup=False))
    text = "This exact text is repeated to test dedup state in async context."

    async def run():
        r1 = await f.aprocess_single(text)
        r2 = await f.aprocess_single(text)
        return r1, r2

    r1, r2 = asyncio.run(run())
    assert r1.is_valid
    assert not r2.is_valid
    assert r2.reason_code == "EXACT_DUPLICATE"


def test_aprocess_single_pii_masked():
    f = TaparashFilter(QualityConfig(
        enable_pii_masking=True,
        entropy_threshold=5.5,
        enable_dlq=False,
    ))
    result = asyncio.run(
        f.aprocess_single("Please contact user@example.com for more information.")
    )
    assert result.is_valid
    assert "user@example.com" not in result.text
    assert "[REDACTED]" in result.text


# ---------------------------------------------------------------------------
# aprocess_batch
# ---------------------------------------------------------------------------

def test_aprocess_batch_returns_batch_result():
    from taparash.config import BatchResult

    f = TaparashFilter(cfg())
    texts = [
        "First valid text chunk for async batch processing test here.",
        "Second valid text chunk that also passes all quality gates.",
    ]
    result = asyncio.run(f.aprocess_batch(texts))
    assert isinstance(result, BatchResult)
    assert len(result.accepted) == 2


def test_aprocess_batch_filters_short_chunks():
    f = TaparashFilter(cfg(min_chunk_length=50))
    texts = [
        "Short.",
        "This text is long enough to pass the minimum length gate easily.",
    ]
    result = asyncio.run(f.aprocess_batch(texts))
    assert len(result.accepted) == 1
    assert len(result.rejected) == 1


def test_aprocess_batch_deduplicates():
    f = TaparashFilter(cfg(enable_exact_dedup=True, enable_fuzzy_dedup=False))
    text = "Repeated text for exact deduplication test in async batch mode."
    result = asyncio.run(f.aprocess_batch([text, text, text]))
    assert len(result.accepted) == 1
    assert len(result.rejected) == 2


def test_aprocess_batch_matches_sync():
    texts = [
        "First text chunk for consistency comparison between sync and async.",
        "Second text chunk that should produce identical results in both modes.",
        "x",  # too short → rejected in both
    ]
    f_sync = TaparashFilter(cfg(enable_fuzzy_dedup=False))
    f_async = TaparashFilter(cfg(enable_fuzzy_dedup=False))

    sync_result = f_sync.process_batch(texts)
    async_result = asyncio.run(f_async.aprocess_batch(texts))

    assert len(sync_result.accepted) == len(async_result.accepted)
    assert len(sync_result.rejected) == len(async_result.rejected)


def test_aprocess_batch_empty_input():
    f = TaparashFilter(cfg())
    result = asyncio.run(f.aprocess_batch([]))
    assert result.total == 0


def test_aprocess_batch_concurrent_calls_do_not_corrupt_state():
    """Multiple concurrent batch calls must not corrupt dedup state."""
    f = TaparashFilter(cfg(enable_exact_dedup=False, enable_fuzzy_dedup=False))

    async def run():
        batches = [
            ["Concurrent batch one text chunk for thread safety test."],
            ["Concurrent batch two text chunk for thread safety test."],
            ["Concurrent batch three text chunk for thread safety test."],
        ]
        results = await asyncio.gather(*[f.aprocess_batch(b) for b in batches])
        return results

    results = asyncio.run(run())
    total_accepted = sum(len(r.accepted) for r in results)
    assert total_accepted == 3  # all unique, all accepted


def test_aprocess_batch_stats_updated():
    f = TaparashFilter(cfg())
    texts = [
        "Valid async batch chunk one for stats testing.",
        "Valid async batch chunk two for stats testing.",
    ]
    asyncio.run(f.aprocess_batch(texts))
    assert f.stats["total_processed"] == 2


# ---------------------------------------------------------------------------
# Coroutine type check
# ---------------------------------------------------------------------------

def test_methods_return_coroutines():
    import inspect

    f = TaparashFilter(cfg())
    coro_single = f.aprocess_single("test text")
    coro_batch = f.aprocess_batch(["test text"])

    assert inspect.iscoroutine(coro_single)
    assert inspect.iscoroutine(coro_batch)

    # Clean up unawaited coroutines
    coro_single.close()
    coro_batch.close()
