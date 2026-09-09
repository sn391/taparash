"""
Test script to verify Taparash installation.

Run this from a different directory or in a clean virtual environment.
"""

import sys
import os

# Remove current directory from path to avoid importing local code
if '' in sys.path:
    sys.path.remove('')
if '.' in sys.path:
    sys.path.remove('.')
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir in sys.path:
    sys.path.remove(current_dir)

print("Testing Taparash installation...\n")

try:
    import taparash
    print(f"✓ Import successful: Taparash v{taparash.__version__}")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

try:
    from taparash import TaparashFilter, QualityConfig
    print("✓ Core imports work")
except ImportError as e:
    print(f"✗ Core imports failed: {e}")
    sys.exit(1)

try:
    config = QualityConfig(enable_dlq=False)
    app = TaparashFilter(config)
    print("✓ TaparashFilter initialization works")
except Exception as e:
    print(f"✗ Initialization failed: {e}")
    sys.exit(1)

try:
    chunks = ['This is a test chunk with sufficient length', 'Too short', 'Another valid test chunk']
    results = app.process_batch(chunks)
    print(f"✓ Processing works: {results.total} chunks processed")
    print(f"  - Accepted: {len(results.accepted)}")
    print(f"  - Rejected: {len(results.rejected)}")
except Exception as e:
    print(f"✗ Processing failed: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("SUCCESS! Taparash v0.3.0 is working correctly!")
print("="*60)
