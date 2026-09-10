"""Base protocol for distributed processing backends."""

from typing import Any, Callable, List, Protocol, Union, runtime_checkable

try:
    from taparash.config import DocumentChunk, FilterResult
except ImportError:
    from config import DocumentChunk, FilterResult  # type: ignore[no-redef]


@runtime_checkable
class DistributedBackend(Protocol):
    """
    Protocol for distributed processing backends.

    Implement this protocol to fan pipeline work across Ray workers,
    Dask bags, a task queue, or any other compute substrate.

    The backend is responsible only for the STATELESS gates (length,
    PII, entropy).  Stateful gates (deduplication) always run locally
    on the coordinator after the backend returns.

    Usage::

        from taparash import TaparashFilter, QualityConfig
        from taparash.backends import RayBackend

        backend = RayBackend(num_cpus=8)
        config = QualityConfig(enable_dlq=False, distributed_backend="ray")
        f = TaparashFilter(config, backend=backend)
        result = f.process_batch(chunks)
    """

    def process_stateless(
        self,
        texts: List[Union[str, "DocumentChunk"]],
        stateless_fn: Callable[[str, str], Any],
    ) -> List[Any]:
        """
        Apply stateless_fn(raw_text, original_text) to each item in texts,
        distributed across workers.  Returns results in the same order as
        the input list.
        """
        ...
