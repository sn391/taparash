"""
Tests for distributed processing backends.

Ray is an optional dependency, so these tests skip gracefully when
ray is not installed.  The RayBackend itself is always importable;
only the actual Ray runtime is optional.
"""

import pytest

try:
    import ray  # noqa: F401
    RAY_AVAILABLE = True
except ImportError:
    RAY_AVAILABLE = False


def test_ray_backend_import():
    """RayBackend can be imported without ray installed (raises on instantiation)."""
    from taparash.backends.ray_backend import RayBackend

    assert RayBackend is not None


def test_ray_backend_missing_ray_raises():
    """If ray is not installed, RayBackend.__init__ raises ImportError."""
    if RAY_AVAILABLE:
        pytest.skip("ray is installed; cannot test missing-ray path")
    from taparash.backends.ray_backend import RayBackend

    with pytest.raises(ImportError, match="ray is required"):
        RayBackend()


def test_distributed_backend_protocol():
    """DistributedBackend and RayBackend are importable from taparash.backends."""
    from taparash.backends import DistributedBackend, RayBackend  # noqa: F401

    assert DistributedBackend is not None
    assert RayBackend is not None


@pytest.mark.skipif(not RAY_AVAILABLE, reason="ray not installed")
def test_ray_backend_process_stateless():
    """RayBackend.process_stateless fans work across Ray tasks."""
    from taparash.backends import RayBackend

    backend = RayBackend(num_cpus=2, shard_size=5)
    texts = [f"chunk number {i}" for i in range(12)]

    def identity_fn(raw_text: str, original_text: str) -> str:
        return raw_text.upper()

    results = backend.process_stateless(texts, identity_fn)
    assert len(results) == 12
    assert all(r == t.upper() for r, t in zip(results, texts))
    backend.shutdown()


@pytest.mark.skipif(not RAY_AVAILABLE, reason="ray not installed")
def test_ray_backend_preserves_order():
    """Results must be in the same order as inputs."""
    from taparash.backends import RayBackend

    backend = RayBackend(num_cpus=2, shard_size=3)
    texts = [str(i) for i in range(20)]

    results = backend.process_stateless(texts, lambda t, _: int(t))
    assert results == list(range(20))
    backend.shutdown()
