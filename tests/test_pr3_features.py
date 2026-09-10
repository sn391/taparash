"""Test script for Phase 3 features: NLI and Contradiction Detection."""

import os

from taparash import TaparashFilter, QualityConfig, DeadLetterQueue


def test_nli_basic():
    """Test basic NLI functionality."""
    print("=" * 70)
    print("TEST 1: NLI Model - Basic Inference")
    print("=" * 70)

    try:
        from taparash.engines.nli import LocalNLI

        print("Initializing NLI model (this may take a moment on first run)...\n")
        nli = LocalNLI()

        test_pairs = [
            ("The cat is on the mat", "The feline is on the rug", "Entailment/Neutral"),
            ("The sky is blue", "The sky is red", "Contradiction"),
            ("I love pizza", "Pizza is delicious", "Neutral/Entailment"),
            ("Water freezes at 0 degrees C", "Water freezes at 100 degrees C", "Contradiction"),
            ("The meeting is at 3pm", "The meeting is at 3pm", "Entailment"),
        ]

        label_names = ["CONTRADICTION", "NEUTRAL", "ENTAILMENT"]

        for premise, hypothesis, expected in test_pairs:
            label, score, all_scores = nli.predict(premise, hypothesis)
            print(f"Premise:    {premise}")
            print(f"Hypothesis: {hypothesis}")
            print(f"Prediction: {label_names[label]} (confidence: {score:.3f})")
            print(f"Expected:   {expected}")
            print()

        print("=" * 70)

    except ImportError:
        print("sentence-transformers not installed.")
        print("Install with: pip install sentence-transformers")
        print("Skipping NLI test.")
        print("=" * 70)


def test_contradiction_detection():
    """Test contradiction detection in pipeline."""
    print("\n\n" + "=" * 70)
    print("TEST 2: Contradiction Detection in Pipeline")
    print("=" * 70)

    try:
        config = QualityConfig(
            min_chunk_length=10,
            check_contradictions=True,
            contradiction_threshold=0.7,
            nli_model_path="cross-encoder/nli-deberta-v3-base",
            enable_entropy_check=False,
            enable_exact_dedup=False,
            enable_fuzzy_dedup=False,
            enable_semantic_dedup=False,
            enable_dlq=False,
        )

        print("Initializing pipeline with contradiction detection...\n")
        app = TaparashFilter(config)

        chunks = [
            "The product launch is scheduled for June 2024.",
            "Our new features are receiving positive feedback from users.",
            "The product launch was cancelled and will not happen in June.",
            "Customer satisfaction ratings have improved by 15%.",
            "Customer satisfaction has declined significantly.",
        ]

        print("Processing chunks with potential contradictions:\n")
        for i, chunk in enumerate(chunks, 1):
            print(f"{i}. {chunk}")
        print()

        results = app.process_batch(chunks)

        print(f"Results:")
        print(f"  Accepted: {len(results.accepted)}")
        print(f"  Rejected: {len(results.rejected)}\n")

        if results.rejected:
            print("Contradictions detected:")
            for r in results.rejected:
                if r.reason_code == "CONTRADICTION":
                    print(f"  - {r.text[:60]}...")
                    print(f"    Contradicts index: {r.metadata.get('contradicting_index')}")
                    print(f"    Confidence: {r.metadata.get('contradiction_confidence', 0):.3f}")
                    print()

        app.print_stats()
        print("=" * 70)

    except ImportError as e:
        print(f"Cannot test: {e}")
        print("Install with: pip install sentence-transformers")
        print("=" * 70)


def test_contradiction_detector_standalone():
    """Test ContradictionDetector class standalone."""
    print("\n\n" + "=" * 70)
    print("TEST 3: ContradictionDetector - Standalone Usage")
    print("=" * 70)

    try:
        from taparash.engines.nli import LocalNLI, ContradictionDetector

        print("Initializing NLI model and contradiction detector...\n")
        nli = LocalNLI()
        detector = ContradictionDetector(
            nli_model=nli,
            threshold=0.7,
            store_texts=True,
            max_context_size=10,
        )

        texts = [
            "The company revenue increased by 20% this quarter.",
            "Sales performance exceeded our targets.",
            "The quarterly revenue decreased significantly.",
            "Our market share has grown steadily.",
        ]

        print("Adding texts to context and checking for contradictions:\n")
        for i, text in enumerate(texts, 1):
            is_valid, contradicting_idx, confidence = detector.add(text)

            print(f"{i}. {text}")
            if not is_valid:
                print(f"   [CONTRADICTION] Contradicts text #{contradicting_idx + 1}")
                print(f"   Confidence: {confidence:.3f}")
            else:
                print(f"   [OK] No contradiction")
            print()

        print(f"Final context size: {detector.get_context_size()}")
        print("=" * 70)

    except ImportError:
        print("sentence-transformers not installed.")
        print("Install with: pip install sentence-transformers")
        print("=" * 70)


def test_coherence_validator():
    """Test CoherenceValidator class."""
    print("\n\n" + "=" * 70)
    print("TEST 4: Coherence Validator")
    print("=" * 70)

    try:
        from taparash.engines.nli import LocalNLI, CoherenceValidator

        print("Initializing coherence validator...\n")
        nli = LocalNLI()
        validator = CoherenceValidator(
            nli_model=nli,
            contradiction_threshold=0.7,
            require_entailment=False,
        )

        context = [
            "The project is in the planning phase.",
            "We are currently gathering requirements from stakeholders.",
        ]

        for text in context:
            validator.add_to_context(text)

        test_texts = [
            "The requirements analysis will be completed next week.",
            "The project has already been deployed to production.",
            "Stakeholder feedback is being collected.",
        ]

        print("Context:")
        for i, text in enumerate(context, 1):
            print(f"  {i}. {text}")
        print()

        print("Testing coherence:\n")
        for text in test_texts:
            is_coherent, reason, confidence = validator.is_coherent(text)
            status = "[COHERENT]" if is_coherent else "[INCOHERENT]"
            print(f"{status} {text}")
            print(f"  Reason: {reason}, Confidence: {confidence:.3f}")
            print()

        print("=" * 70)

    except ImportError:
        print("sentence-transformers not installed.")
        print("Install with: pip install sentence-transformers")
        print("=" * 70)


def test_batch_contradiction_check():
    """Test checking for internal contradictions in a batch."""
    print("\n\n" + "=" * 70)
    print("TEST 5: Batch Internal Contradiction Check")
    print("=" * 70)

    try:
        from taparash.engines.nli import LocalNLI, ContradictionDetector

        print("Checking batch for internal contradictions...\n")
        nli = LocalNLI()
        detector = ContradictionDetector(
            nli_model=nli,
            threshold=0.7,
            store_texts=False,
        )

        batch = [
            "The server is running smoothly.",
            "All systems are operational.",
            "The server has crashed and is offline.",
            "Database backups completed successfully.",
            "The database backup process failed.",
        ]

        print("Batch texts:")
        for i, text in enumerate(batch, 1):
            print(f"  {i}. {text}")
        print()

        contradictions = detector.check_batch_internal_contradictions(
            batch,
            return_pairs=True,
        )

        if contradictions:
            print(f"Found {len(contradictions)} contradictions within batch:\n")
            for c in contradictions:
                print(f"  Texts #{c['index1'] + 1} and #{c['index2'] + 1} contradict:")
                print(f"    A: {c['text1']}")
                print(f"    B: {c['text2']}")
                print(f"    Confidence: {c['confidence']:.3f}")
                print()
        else:
            print("No contradictions found within batch.")

        print("=" * 70)

    except ImportError:
        print("sentence-transformers not installed.")
        print("Install with: pip install sentence-transformers")
        print("=" * 70)


def test_full_pipeline_with_contradictions():
    """Test full pipeline with all filters including contradictions."""
    print("\n\n" + "=" * 70)
    print("TEST 6: Full Pipeline with Contradiction Detection")
    print("=" * 70)

    try:
        config = QualityConfig(
            min_chunk_length=20,
            enable_pii_masking=True,
            enable_entropy_check=True,
            enable_exact_dedup=True,
            enable_fuzzy_dedup=False,
            enable_semantic_dedup=False,
            check_contradictions=True,
            contradiction_threshold=0.75,
            nli_model_path="cross-encoder/nli-deberta-v3-base",
            enable_dlq=True,
            dlq_path="test_pr3_dlq.db",
        )

        print("Testing full pipeline with all Phase 1-3 features...\n")
        app = TaparashFilter(config)

        chunks = [
            "The quarterly revenue increased by 25% year over year.",
            "Customer retention rates improved significantly this quarter.",
            "Revenue declined sharply compared to last year.",
            "Contact support at support@example.com for assistance.",  # PII
            "Short",  # Too short
            "The quarterly revenue increased by 25% year over year.",  # Duplicate
            "Our team successfully launched three new features.",
            "New feature rollout was delayed indefinitely.",
        ]

        results = app.process_batch(chunks)

        print("Results:")
        print(f"  Total processed: {len(chunks)}")
        print(f"  Accepted: {len(results.accepted)}")
        print(f"  Rejected: {len(results.rejected)}\n")

        print("Rejection breakdown:")
        rejection_counts = {}
        for r in results.rejected:
            rejection_counts[r.reason_code] = rejection_counts.get(r.reason_code, 0) + 1

        for reason, count in rejection_counts.items():
            print(f"  {reason}: {count}")

        print()
        app.print_stats()

        dlq = DeadLetterQueue("test_pr3_dlq.db")
        print("\nDead Letter Queue Summary:")
        dlq.print_summary()

        print("=" * 70)

        if os.path.exists("test_pr3_dlq.db"):
            os.remove("test_pr3_dlq.db")
            print("\nCleaned up test database.")

    except ImportError as e:
        print(f"Cannot test: {e}")
        print("Install with: pip install sentence-transformers")
        print("=" * 70)


if __name__ == "__main__":
    print("\n")
    print("=" * 70)
    print("PHASE 3 FEATURE TESTS")
    print("NLI and Contradiction Detection")
    print("=" * 70)
    print("\nNote: First run will download NLI models (~400MB)")
    print("Subsequent runs will use cached models.\n")

    try:
        test_nli_basic()
        test_contradiction_detection()
        test_contradiction_detector_standalone()
        test_coherence_validator()
        test_batch_contradiction_check()
        test_full_pipeline_with_contradictions()

        print("\n\n" + "=" * 70)
        print("ALL PHASE 3 TESTS COMPLETED")
        print("=" * 70)

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
