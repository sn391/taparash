"""Example usage of Taparash as described in taparash.md"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from taparash import TaparashFilter, QualityConfig

# 1. Initialize Configuration (100% Offline)
config = QualityConfig(
    min_chunk_length=20,
    max_chunk_length=2000,
    entropy_threshold=4.5,  # Shannon Entropy cutoff for gibberish
    dedup_threshold=0.88,   # Semantic duplicate threshold
    check_contradictions=False,  # Not yet implemented
    enable_pii_masking=True
)

# 2. Instantiate Taparash Engine
app = TaparashFilter(config=config)

# 3. Sample Data Chunks
chunks = [
    "The quarterly revenue for Q3 grew by 15% reaching 4.2M EUR.",
    "The quarterly revenue for Q3 grew by 15% reaching 4.2M EUR.",  # Duplicate
    "Q3 revenue dropped by 50% causing major losses.",  # Different content
    "a8f9#$s82kjsdf092348572390485723904857239048572390485",  # Gibberish/Entropy fail
    "Contact us at sales@company.com for pricing information.",  # PII
]

# 4. Filter Pipeline Execution
results = app.process_batch(chunks)

print(f"Clean Chunks Accepted: {len(results.accepted)}")
print(f"Rejected Chunks: {len(results.rejected)}")
print()

# Inspect Rejections & DLQ Reasons
print("REJECTED CHUNKS:")
for item in results.rejected:
    print(f"  Text: '{item.text[:50]}...'")
    print(f"  Reason: {item.reason_code}")
    print(f"  Detail: {item.reason_detail}")
    print()

print("ACCEPTED CHUNKS:")
for item in results.accepted:
    print(f"  Original: '{item.original_text[:50]}...'")
    print(f"  Processed: '{item.text[:50]}...'")
    if item.metadata.get('pii_masked_count', 0) > 0:
        print(f"  PII Masked: {item.metadata['pii_masked_count']} items")
    print()

# Show statistics
print()
app.print_stats()
