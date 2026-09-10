"""Tests for the LangChain integration.

langchain-core is an optional dependency, so tests skip gracefully when
it is not installed. The transformer class itself is always importable;
only instantiation requires langchain-core.
"""

import pytest

try:
    from langchain_core.documents import Document
    _LANGCHAIN_AVAILABLE = True
except ImportError:
    _LANGCHAIN_AVAILABLE = False

skip_no_langchain = pytest.mark.skipif(
    not _LANGCHAIN_AVAILABLE, reason="langchain-core not installed"
)


def test_transformer_importable():
    from taparash.integrations.langchain import TaparashDocumentTransformer

    assert TaparashDocumentTransformer is not None


def test_transformer_raises_without_langchain():
    if _LANGCHAIN_AVAILABLE:
        pytest.skip("langchain-core is installed; cannot test missing-langchain path")

    from taparash.integrations.langchain import TaparashDocumentTransformer

    with pytest.raises(ImportError, match="langchain-core"):
        TaparashDocumentTransformer()


@skip_no_langchain
def test_accepted_documents_returned():
    from taparash.integrations.langchain import TaparashDocumentTransformer
    from taparash import QualityConfig

    t = TaparashDocumentTransformer(
        config=QualityConfig(enable_pii_masking=False, enable_dlq=False)
    )
    docs = [
        Document(page_content="This is a clean, useful chunk of text for testing."),
        Document(page_content="Another valid piece of content here."),
    ]
    result = t.transform_documents(docs)
    assert len(result) == 2
    assert result[0].page_content == docs[0].page_content


@skip_no_langchain
def test_short_chunks_rejected():
    from taparash.integrations.langchain import TaparashDocumentTransformer
    from taparash import QualityConfig

    t = TaparashDocumentTransformer(
        config=QualityConfig(min_chunk_length=50, enable_dlq=False)
    )
    docs = [
        Document(page_content="Too short."),
        Document(page_content="This sentence is long enough to pass the minimum length gate easily."),
    ]
    result = t.transform_documents(docs)
    assert len(result) == 1
    assert "long enough" in result[0].page_content


@skip_no_langchain
def test_duplicate_documents_deduplicated():
    from taparash.integrations.langchain import TaparashDocumentTransformer
    from taparash import QualityConfig

    t = TaparashDocumentTransformer(
        config=QualityConfig(
            enable_exact_dedup=True,
            enable_fuzzy_dedup=False,
            enable_pii_masking=False,
            enable_dlq=False,
        )
    )
    text = "This is an exact duplicate sentence that will appear twice in the batch."
    docs = [Document(page_content=text), Document(page_content=text)]
    result = t.transform_documents(docs)
    assert len(result) == 1


@skip_no_langchain
def test_pii_masking_applied_to_page_content():
    from taparash.integrations.langchain import TaparashDocumentTransformer
    from taparash import QualityConfig

    t = TaparashDocumentTransformer(
        config=QualityConfig(
            enable_pii_masking=True,
            pii_replacement_token="[REDACTED]",
            entropy_threshold=5.5,  # raised: [REDACTED] token lifts entropy slightly
            enable_dlq=False,
        )
    )
    docs = [Document(page_content="Contact us at secret@example.com for details.")]
    result = t.transform_documents(docs)
    assert len(result) == 1
    assert "[REDACTED]" in result[0].page_content
    assert "secret@example.com" not in result[0].page_content


@skip_no_langchain
def test_original_metadata_preserved():
    from taparash.integrations.langchain import TaparashDocumentTransformer
    from taparash import QualityConfig

    t = TaparashDocumentTransformer(
        config=QualityConfig(enable_pii_masking=False, enable_dlq=False)
    )
    docs = [
        Document(
            page_content="Valid content that should pass all quality gates easily.",
            metadata={"source": "wiki", "page": 3},
        )
    ]
    result = t.transform_documents(docs)
    assert result[0].metadata["source"] == "wiki"
    assert result[0].metadata["page"] == 3


@skip_no_langchain
def test_add_filter_metadata_flag():
    from taparash.integrations.langchain import TaparashDocumentTransformer
    from taparash import QualityConfig

    t = TaparashDocumentTransformer(
        config=QualityConfig(
            enable_pii_masking=True,
            entropy_threshold=5.5,  # raised: [REDACTED] token lifts entropy slightly
            enable_dlq=False,
        ),
        add_filter_metadata=True,
    )
    docs = [
        Document(page_content="Clean content with no PII whatsoever in it."),
        Document(page_content="Email us at info@company.com for more information."),
    ]
    result = t.transform_documents(docs)
    assert all(r.metadata.get("taparash_accepted") is True for r in result)
    # First doc: no PII masked; second doc: PII was masked
    assert result[0].metadata["taparash_pii_masked"] is False
    assert result[1].metadata["taparash_pii_masked"] is True


@skip_no_langchain
def test_empty_input_returns_empty():
    from taparash.integrations.langchain import TaparashDocumentTransformer

    t = TaparashDocumentTransformer()
    result = t.transform_documents([])
    assert list(result) == []


@skip_no_langchain
def test_async_transform_documents():
    import asyncio
    from taparash.integrations.langchain import TaparashDocumentTransformer
    from taparash import QualityConfig

    t = TaparashDocumentTransformer(
        config=QualityConfig(enable_pii_masking=False, enable_dlq=False)
    )
    docs = [Document(page_content="Async content that should pass the quality gate.")]

    result = asyncio.run(t.atransform_documents(docs))
    assert len(result) == 1


@skip_no_langchain
def test_is_base_document_transformer():
    from langchain_core.documents.transformers import BaseDocumentTransformer
    from taparash.integrations.langchain import TaparashDocumentTransformer

    t = TaparashDocumentTransformer()
    assert isinstance(t, BaseDocumentTransformer)
