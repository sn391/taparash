"""LangChain integration for Taparash.

Provides a BaseDocumentTransformer that runs the full taparash quality-filtering
pipeline (PII masking, dedup, entropy, length) on LangChain Document sequences.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional, Sequence

try:
    from langchain_core.documents import Document
    from langchain_core.documents.transformers import BaseDocumentTransformer
    _LANGCHAIN_AVAILABLE = True
except ImportError:
    _LANGCHAIN_AVAILABLE = False
    Document = None  # type: ignore[assignment,misc]
    BaseDocumentTransformer = object  # type: ignore[assignment,misc]

try:
    from taparash.config import QualityConfig
    from taparash.pipeline import TaparashFilter
except ImportError:
    from ..config import QualityConfig  # type: ignore[no-redef]
    from ..pipeline import TaparashFilter  # type: ignore[no-redef]


class TaparashDocumentTransformer(BaseDocumentTransformer):  # type: ignore[misc]
    """LangChain ``BaseDocumentTransformer`` backed by taparash quality filtering.

    Accepted documents are returned with ``page_content`` potentially PII-masked.
    Rejected documents are silently dropped. Deduplication state accumulates
    across ``transform_documents`` calls — create a new instance to reset it.

    Args:
        config: ``QualityConfig`` to control which gates are active.
                Defaults to taparash's standard defaults.
        add_filter_metadata: When ``True``, inject ``taparash_accepted`` and
                             ``taparash_pii_masked`` keys into each accepted
                             document's metadata.

    Example::

        from taparash.integrations.langchain import TaparashDocumentTransformer
        from taparash import QualityConfig

        transformer = TaparashDocumentTransformer(
            config=QualityConfig(enable_pii_masking=True, enable_dlq=False),
            add_filter_metadata=True,
        )
        clean_docs = transformer.transform_documents(raw_docs)

    LangChain LCEL usage::

        from langchain_core.runnables import RunnablePassthrough

        chain = loader | transformer | embedder | retriever
    """

    def __init__(
        self,
        config: Optional[QualityConfig] = None,
        add_filter_metadata: bool = False,
    ) -> None:
        if not _LANGCHAIN_AVAILABLE:
            raise ImportError(
                "langchain-core is required for TaparashDocumentTransformer. "
                "Install it with: pip install taparash[langchain]"
            )
        self._filter = TaparashFilter(config or QualityConfig())
        self._add_metadata = add_filter_metadata

    def transform_documents(
        self,
        documents: Sequence["Document"],
        **kwargs: Any,
    ) -> Sequence["Document"]:
        """Filter documents synchronously, returning only accepted ones."""
        output = []
        for doc in documents:
            result = self._filter.process_single(doc.page_content)
            if not result.is_valid:
                continue
            new_meta = doc.metadata.copy()
            if self._add_metadata:
                new_meta["taparash_accepted"] = True
                new_meta["taparash_pii_masked"] = result.text != doc.page_content
            output.append(Document(page_content=result.text, metadata=new_meta))
        return output

    async def atransform_documents(
        self,
        documents: Sequence["Document"],
        **kwargs: Any,
    ) -> Sequence["Document"]:
        """Filter documents asynchronously (runs sync transform in a thread)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.transform_documents, documents
        )
