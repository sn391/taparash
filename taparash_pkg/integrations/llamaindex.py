"""LlamaIndex integration for Taparash.

Provides a BaseNodePostprocessor that runs the full taparash quality-filtering
pipeline on LlamaIndex NodeWithScore sequences.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

try:
    from llama_index.core.postprocessor.types import BaseNodePostprocessor
    from llama_index.core.schema import NodeWithScore, QueryBundle
    from pydantic import PrivateAttr
    _LLAMAINDEX_AVAILABLE = True
except ImportError:
    _LLAMAINDEX_AVAILABLE = False
    BaseNodePostprocessor = object  # type: ignore[assignment,misc]
    NodeWithScore = None  # type: ignore[assignment,misc]
    QueryBundle = None  # type: ignore[assignment,misc]

try:
    from taparash.config import QualityConfig
    from taparash.pipeline import TaparashFilter
except ImportError:
    from ..config import QualityConfig  # type: ignore[no-redef]
    from ..pipeline import TaparashFilter  # type: ignore[no-redef]

if TYPE_CHECKING:
    pass


class TaparashNodePostprocessor(BaseNodePostprocessor):  # type: ignore[misc]
    """LlamaIndex ``BaseNodePostprocessor`` backed by taparash quality filtering.

    Filters a list of ``NodeWithScore`` objects, returning only those whose
    text passes all configured quality gates.  PII masking is applied in-place
    on the node's text content.  Rejected nodes are silently dropped.

    Deduplication state accumulates across ``postprocess_nodes`` calls — create
    a new instance to reset between independent document sets.

    Args:
        config: ``QualityConfig`` controlling which gates are active.
                Defaults to taparash's standard defaults.
        add_filter_metadata: When ``True``, inject ``taparash_accepted`` and
                             ``taparash_pii_masked`` into each accepted node's
                             ``metadata`` dict.

    Example::

        from taparash.integrations.llamaindex import TaparashNodePostprocessor
        from taparash import QualityConfig

        postprocessor = TaparashNodePostprocessor(
            config=QualityConfig(enable_pii_masking=True, enable_dlq=False),
            add_filter_metadata=True,
        )

        # Use in a RetrieverQueryEngine
        query_engine = index.as_query_engine(
            node_postprocessors=[postprocessor]
        )

        # Or call directly
        filtered_nodes = postprocessor.postprocess_nodes(raw_nodes)
    """

    add_filter_metadata: bool = False

    # Private — not serialised with the pydantic model
    if _LLAMAINDEX_AVAILABLE:
        _filter: "TaparashFilter" = PrivateAttr()

    def __init__(
        self,
        config: Optional["QualityConfig"] = None,
        add_filter_metadata: bool = False,
        **kwargs,
    ) -> None:
        if not _LLAMAINDEX_AVAILABLE:
            raise ImportError(
                "llama-index-core is required for TaparashNodePostprocessor. "
                "Install it with: pip install taparash[llamaindex]"
            )
        super().__init__(add_filter_metadata=add_filter_metadata, **kwargs)
        self._filter = TaparashFilter(config or QualityConfig())

    def _postprocess_nodes(
        self,
        nodes: List["NodeWithScore"],
        query_bundle: Optional["QueryBundle"] = None,
    ) -> List["NodeWithScore"]:
        """Filter nodes synchronously, returning only accepted ones."""
        output = []
        for nws in nodes:
            text = nws.node.get_content()
            result = self._filter.process_single(text)
            if not result.is_valid:
                continue

            # Copy node to avoid mutating the input
            try:
                new_node = nws.node.model_copy()   # pydantic v2
            except AttributeError:
                new_node = nws.node.copy()         # pydantic v1

            new_node.text = result.text

            if self.add_filter_metadata:
                new_node.metadata = dict(new_node.metadata)
                new_node.metadata["taparash_accepted"] = True
                new_node.metadata["taparash_pii_masked"] = result.text != text

            output.append(NodeWithScore(node=new_node, score=nws.score))
        return output
