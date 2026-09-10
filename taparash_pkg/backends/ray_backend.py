"""Ray-based distributed backend for Taparash stateless pipeline gates."""

from typing import Any, Callable, List, Optional, Union


class RayBackend:
    """
    Distribute stateless pipeline gates (length, PII, entropy) across Ray workers.

    Stateful gates (dedup, contradiction) always run on the coordinator
    process because they require shared mutable state.

    Each Ray task processes a contiguous shard of the input list and returns
    results in original input order.  The coordinator assembles these and
    runs stateful gates sequentially.

    Args:
        num_cpus: Number of CPUs to request when initialising Ray.
                  ``None`` lets Ray auto-detect.
        shard_size: Number of items per Ray task (tune for your cluster).
        ray_init_kwargs: Extra kwargs forwarded to ``ray.init()``.

    Example::

        from taparash.backends import RayBackend
        from taparash import TaparashFilter, QualityConfig

        backend = RayBackend(num_cpus=4, shard_size=100)
        config = QualityConfig(enable_dlq=False, distributed_backend="ray")
        f = TaparashFilter(config, backend=backend)
        results = f.process_batch(large_document_list)
    """

    def __init__(
        self,
        num_cpus: Optional[int] = None,
        shard_size: int = 200,
        **ray_init_kwargs: Any,
    ) -> None:
        try:
            import ray  # noqa: F401 — presence check; deferred import avoids hard dep at import time
        except ImportError as exc:
            raise ImportError(
                "ray is required for RayBackend.  "
                "Install it with:  pip install 'taparash[distributed]'"
            ) from exc
        self.num_cpus = num_cpus
        self.shard_size = shard_size
        self._ray_init_kwargs = ray_init_kwargs

    def _ensure_ray(self) -> None:
        import ray

        if not ray.is_initialized():
            init_kwargs: dict = {}
            if self.num_cpus is not None:
                init_kwargs["num_cpus"] = self.num_cpus
            init_kwargs.update(self._ray_init_kwargs)
            ray.init(ignore_reinit_error=True, **init_kwargs)

    def process_stateless(
        self,
        texts: List[Union[str, Any]],  # Union[str, DocumentChunk]
        stateless_fn: Callable[[str, str], Any],
    ) -> List[Any]:
        """
        Apply stateless_fn to each item distributed across Ray workers.

        Returns results in original input order.
        """
        import ray

        self._ensure_ray()

        @ray.remote
        def _shard_task(shard: list, fn: Callable) -> list:
            return [
                fn(item, item) if isinstance(item, str) else fn(item.text, item.text)
                for item in shard
            ]

        shards = [
            texts[i : i + self.shard_size]
            for i in range(0, len(texts), self.shard_size)
        ]
        futures = [_shard_task.remote(shard, stateless_fn) for shard in shards]
        nested: List[list] = ray.get(futures)
        return [item for sub in nested for item in sub]

    def shutdown(self) -> None:
        """Shut down the Ray runtime (no-op if not initialised or not installed)."""
        try:
            import ray

            if ray.is_initialized():
                ray.shutdown()
        except ImportError:
            pass
