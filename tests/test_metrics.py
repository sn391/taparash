"""Tests for Observability/Telemetry (PipelineMetrics + metrics_callback)."""

from taparash import TaparashFilter, QualityConfig, PipelineMetrics


def test_metrics_callback_invoked():
    received = []

    def cb(m: PipelineMetrics):
        received.append(m)

    config = QualityConfig(enable_dlq=False, metrics_callback=cb)
    f = TaparashFilter(config)
    chunks = [
        "This is a sufficiently long chunk of text for testing purposes.",
        "Another valid text chunk that should pass all quality gates easily.",
        "x",  # too short - rejected
    ]
    f.process_batch(chunks)
    assert len(received) == 1
    m = received[0]
    assert isinstance(m, PipelineMetrics)
    assert m.total == 3
    assert m.accepted == 2
    assert m.rejected_length == 1
    assert m.rejected == 1
    assert m.wall_time_ms >= 0.0


def test_metrics_as_dict():
    config = QualityConfig(enable_dlq=False)
    f = TaparashFilter(config)
    received = []
    config.metrics_callback = received.append
    f.process_batch(["Valid chunk with enough length for passing filters."])
    assert len(received) == 1
    d = received[0].as_dict()
    assert "total" in d
    assert "acceptance_rate" in d
    assert "wall_time_ms" in d


def test_metrics_acceptance_rate():
    received = []
    config = QualityConfig(enable_dlq=False, metrics_callback=lambda m: received.append(m))
    f = TaparashFilter(config)
    f.process_batch([
        "Valid chunk one with sufficient text length.",
        "Valid chunk two with sufficient text length.",
    ])
    m = received[0]
    assert m.acceptance_rate == 100.0


def test_metrics_no_callback_no_error():
    config = QualityConfig(enable_dlq=False)  # no callback
    f = TaparashFilter(config)
    result = f.process_batch(["Valid chunk with enough length for passing filters."])
    assert result.total == 1


def test_metrics_process_single():
    received = []
    config = QualityConfig(enable_dlq=False, metrics_callback=lambda m: received.append(m))
    f = TaparashFilter(config)
    f.process_single("A single valid chunk with sufficient length to pass.")
    assert len(received) == 1
    assert received[0].total == 1


def test_bad_callback_does_not_crash_pipeline():
    def bad_cb(m):
        raise RuntimeError("intentional error")

    config = QualityConfig(enable_dlq=False, metrics_callback=bad_cb)
    f = TaparashFilter(config)
    result = f.process_batch(["Valid chunk that should still be processed fine."])
    assert result.total == 1
