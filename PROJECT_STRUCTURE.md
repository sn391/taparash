# Taparash Project Structure

## Directory Layout

```
taparash/
├── core/                           # Core functionality modules
│   ├── __init__.py                # Exports all core functions
│   ├── deduplication.py           # SHA256 & MinHash deduplication
│   ├── entropy.py                 # Shannon entropy calculations
│   ├── pii.py                     # PII detection & masking [NEW]
│   └── README_DEDUPLICATION.md    # Deduplication documentation
├── __init__.py                    # Package initialization & exports
├── config.py                      # Configuration management [NEW]
├── pipeline.py                    # Main TaparashFilter pipeline [NEW]
├── CLAUDE.md                      # Claude Code project guidelines
├── taparash.md                    # Project overview & documentation
├── PROJECT_STRUCTURE.md           # This file
├── PR1_IMPLEMENTATION_REPORT.md   # Priority 1 implementation report [NEW]
├── example_usage.py               # Example usage from taparash.md [NEW]
├── demo_deduplication.py          # Deduplication demo script
├── test_deduplication.py          # Deduplication tests
├── test_deduplication_advanced.py # Advanced deduplication tests
└── test_pipeline.py               # Full pipeline tests [NEW]

```

## Implementation Status

### ✅ Completed (Priority 1) - 55%
- Configuration system (`config.py`)
- PII masking (`core/pii.py`)
- Main pipeline (`pipeline.py`)
- Entropy filtering (from earlier phase)
- Exact deduplication (from earlier phase)
- Fuzzy deduplication (from earlier phase)

### ⏳ Pending (Priority 2) - 20%
- Dead Letter Queue (`dlq.py`)
- Local embeddings (`engines/embeddings.py`)
- Semantic deduplication

### ⏳ Pending (Priority 3) - 25%
- Contradiction detection (`engines/nli.py`)

## Files Removed

- `tests/` - Empty directory (removed)
- `src/` - Old directory structure (removed)

## Key Files

### Core Implementation
- **deduplication.py** (9,541 bytes): Complete exact & fuzzy deduplication
- **entropy.py** (1,453 bytes): Shannon entropy calculations
- **pii.py** (8,976 bytes): PII detection & masking with regex [NEW]
- **config.py** (4,187 bytes): Configuration management [NEW]
- **pipeline.py** (9,012 bytes): Main TaparashFilter orchestration [NEW]

### Documentation
- **taparash.md**: Project overview, features, architecture
- **README_DEDUPLICATION.md**: Complete deduplication API documentation
- **CLAUDE.md**: Development guidelines
- **PR1_IMPLEMENTATION_REPORT.md**: Detailed PR1 completion report [NEW]

### Testing & Demos
- **test_deduplication.py**: Basic deduplication tests
- **test_deduplication_advanced.py**: Advanced deduplication tests
- **demo_deduplication.py**: Deduplication usage demonstration
- **test_pipeline.py**: Comprehensive pipeline tests [NEW]
- **example_usage.py**: Example from taparash.md spec [NEW]

## Import Usage

```python
# Direct imports from package root
from taparash import TaparashFilter, QualityConfig
from taparash import deduplicate_exact, deduplicate_fuzzy
from taparash import PIIMasker, mask_pii
from taparash import shannon_entropy, is_gibberish

# Or from specific modules
from taparash.core import deduplicate_exact, PIIMasker
from taparash.config import QualityConfig, FilterResult, BatchResult
from taparash.pipeline import TaparashFilter
```

## Running Tests

```bash
cd C:\Users\sn391\Documents\AgenticAI\taparash

# Run all deduplication tests
python test_deduplication.py
python test_deduplication_advanced.py
python demo_deduplication.py

# Run pipeline tests (PR1)
python test_pipeline.py

# Run example usage
python example_usage.py
```

## Package Version

Current version: **0.1.0**

## Processing Pipeline

The TaparashFilter processes text through 7 gates:

1. ✅ **Length Validation** - Min/max length checks
2. ✅ **PII Masking** - Regex-based sanitization
3. ✅ **Entropy Check** - Gibberish detection (Shannon entropy)
4. ✅ **Exact Deduplication** - SHA-256 hashing
5. ✅ **Fuzzy Deduplication** - MinHash LSH
6. ⏳ **Semantic Deduplication** - Vector clustering (PR2)
7. ⏳ **Contradiction Detection** - NLI model (PR3)

## Rejection Reason Codes

- `LENGTH_TOO_SHORT` - Below minimum length
- `LENGTH_TOO_LONG` - Above maximum length
- `HIGH_ENTROPY` - Entropy exceeds threshold (gibberish)
- `EXACT_DUPLICATE` - SHA-256 hash match
- `FUZZY_DUPLICATE` - MinHash similarity match
- `SEMANTIC_DUPLICATE` - (Not yet implemented)
- `CONTRADICTION` - (Not yet implemented)
