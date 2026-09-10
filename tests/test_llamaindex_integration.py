"""Tests for the LlamaIndex integration.

llama-index-core is optional, so all tests skip gracefully when absent.
"""

import pytest

try:
    from llama_index.core.schema import NodeWithScore, TextNode
    _LLAMAINDEX_AVAILABLE = True
except ImportError:
    _LLAMAINDEX_AVAILABLE = False

skip_no_llamaindex = pytest.mark.skipif(
    not _LLAMAINDEX_AVAILABLE, reason="llama-index-core not installed"
)


def make_nodes(*texts, score=1.0):
    return [NodeWithScore(node=TextNode(text=t), score=score) for t in texts]


# ---------------------------------------------------------------------------
# Import / instantiation
# ---------------------------------------------------------------------------

def test_postprocessor_importable():
    from taparash.integrations.llamaindex import TaparashNodePostprocessor
    assert TaparashNodePostprocessor is not None


def test_postprocessor_raises_without_llamaindex():
    if _LLAMAINDEX_AVAILABLE:
        pytest.skip("llama-index-core is installed; cannot test missing path")
    from taparash.integrations.llamaindex import TaparashNodePostprocessor
    with pytest.raises(ImportError, match="llama-index-core"):
        TaparashNodePostprocessor()


@skip_no_llamaindex
def test_is_base_node_postprocessor():
    from llama_index.core.postprocessor.types import BaseNodePostprocessor
    from taparash.integrations.llamaindex import TaparashNodePostprocessor
    p = TaparashNodePostprocessor()
    assert isinstance(p, BaseNodePostprocessor)


# ---------------------------------------------------------------------------
# Filtering behaviour
# ---------------------------------------------------------------------------

@skip_no_llamaindex
def test_accepted_nodes_returned():
    from taparash.integrations.llamaindex import TaparashNodePostprocessor
    from taparash import QualityConfig

    p = TaparashNodePostprocessor(
        config=QualityConfig(enable_pii_masking=False, enable_dlq=False)
    )
    nodes = make_nodes(
        "This is a clean and valid text chunk for the pipeline.",
        "Another valid piece of content that should pass all gates.",
    )
    result = p.postprocess_nodes(nodes)
    assert len(result) == 2
    assert result[0].node.text == nodes[0].node.text


@skip_no_llamaindex
def test_short_nodes_rejected():
    from taparash.integrations.llamaindex import TaparashNodePostprocessor
    from taparash import QualityConfig

    p = TaparashNodePostprocessor(
        config=QualityConfig(min_chunk_length=50, enable_dlq=False)
    )
    nodes = make_nodes(
        "Too short.",
        "This sentence is definitely long enough to pass the minimum length gate.",
    )
    result = p.postprocess_nodes(nodes)
    assert len(result) == 1
    assert "long enough" in result[0].node.text


@skip_no_llamaindex
def test_duplicate_nodes_deduplicated():
    from taparash.integrations.llamaindex import TaparashNodePostprocessor
    from taparash import QualityConfig

    p = TaparashNodePostprocessor(
        config=QualityConfig(
            enable_exact_dedup=True,
            enable_fuzzy_dedup=False,
            enable_pii_masking=False,
            enable_dlq=False,
        )
    )
    text = "Exact duplicate text that will appear twice in the node list."
    result = p.postprocess_nodes(make_nodes(text, text))
    assert len(result) == 1


@skip_no_llamaindex
def test_pii_masking_applied_to_node_text():
    from taparash.integrations.llamaindex import TaparashNodePostprocessor
    from taparash import QualityConfig

    p = TaparashNodePostprocessor(
        config=QualityConfig(
            enable_pii_masking=True,
            pii_replacement_token="[REDACTED]",
            entropy_threshold=5.5,
            enable_dlq=False,
        )
    )
    nodes = make_nodes("Contact support at help@company.com for assistance.")
    result = p.postprocess_nodes(nodes)
    assert len(result) == 1
    assert "[REDACTED]" in result[0].node.text
    assert "help@company.com" not in result[0].node.text


@skip_no_llamaindex
def test_original_node_not_mutated():
    from taparash.integrations.llamaindex import TaparashNodePostprocessor
    from taparash import QualityConfig

    p = TaparashNodePostprocessor(
        config=QualityConfig(
            enable_pii_masking=True,
            entropy_threshold=5.5,
            enable_dlq=False,
        )
    )
    original_text = "Email admin@example.com for more information please."
    nodes = make_nodes(original_text)
    p.postprocess_nodes(nodes)
    # Original node must not be modified
    assert nodes[0].node.text == original_text


@skip_no_llamaindex
def test_node_score_preserved():
    from taparash.integrations.llamaindex import TaparashNodePostprocessor
    from taparash import QualityConfig

    p = TaparashNodePostprocessor(
        config=QualityConfig(enable_pii_masking=False, enable_dlq=False)
    )
    nodes = make_nodes("Valid content for testing score preservation.", score=0.87)
    result = p.postprocess_nodes(nodes)
    assert len(result) == 1
    assert result[0].score == pytest.approx(0.87)


@skip_no_llamaindex
def test_node_metadata_preserved():
    from taparash.integrations.llamaindex import TaparashNodePostprocessor
    from taparash import QualityConfig

    p = TaparashNodePostprocessor(
        config=QualityConfig(enable_pii_masking=False, enable_dlq=False)
    )
    node = NodeWithScore(
        node=TextNode(
            text="Valid content that should pass all the quality gates easily.",
            metadata={"source": "wiki", "page": 5},
        ),
        score=1.0,
    )
    result = p.postprocess_nodes([node])
    assert result[0].node.metadata["source"] == "wiki"
    assert result[0].node.metadata["page"] == 5


@skip_no_llamaindex
def test_add_filter_metadata_flag():
    from taparash.integrations.llamaindex import TaparashNodePostprocessor
    from taparash import QualityConfig

    p = TaparashNodePostprocessor(
        config=QualityConfig(
            enable_pii_masking=True,
            entropy_threshold=5.5,
            enable_dlq=False,
        ),
        add_filter_metadata=True,
    )
    nodes = make_nodes(
        "Clean content with absolutely no PII in it at all.",
        "Reach us at contact@business.org for support questions.",
    )
    result = p.postprocess_nodes(nodes)
    assert all(r.node.metadata.get("taparash_accepted") is True for r in result)
    assert result[0].node.metadata["taparash_pii_masked"] is False
    assert result[1].node.metadata["taparash_pii_masked"] is True


@skip_no_llamaindex
def test_empty_input_returns_empty():
    from taparash.integrations.llamaindex import TaparashNodePostprocessor
    p = TaparashNodePostprocessor()
    assert p.postprocess_nodes([]) == []


@skip_no_llamaindex
def test_query_bundle_argument_accepted():
    from llama_index.core.schema import QueryBundle
    from taparash.integrations.llamaindex import TaparashNodePostprocessor
    from taparash import QualityConfig

    p = TaparashNodePostprocessor(
        config=QualityConfig(enable_pii_masking=False, enable_dlq=False)
    )
    nodes = make_nodes("Valid content for query bundle argument test here.")
    qb = QueryBundle(query_str="test query")
    result = p.postprocess_nodes(nodes, query_bundle=qb)
    assert len(result) == 1
