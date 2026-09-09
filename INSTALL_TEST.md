# How to Test Taparash Installation

## The Problem

When you run `python -c "import taparash..."` from the **project directory**, Python imports the LOCAL `taparash/` folder (which is old and broken) instead of the INSTALLED package.

## ✅ Solution 1: Test from Different Directory (RECOMMENDED)

```bash
# Move to a different directory
cd ~

# Or create a temp directory
mkdir /tmp/test_taparash
cd /tmp/test_taparash

# Now test the installation
python -c "import taparash; print(f'Taparash v{taparash.__version__} installed successfully!')"
```

## ✅ Solution 2: Use the Test Script

I created a test script that removes the current directory from Python's path:

```bash
cd C:/Users/sn391/Documents/AgenticAI/taparash
python test_installation.py
```

## ✅ Solution 3: Test in Virtual Environment (Most Reliable)

```bash
# Create a fresh virtual environment OUTSIDE the project
cd ~
python -m venv test_taparash_env

# Activate it
# On Windows:
test_taparash_env\Scripts\activate
# On Linux/Mac:
source test_taparash_env/bin/activate

# Install taparash
pip install C:/Users/sn391/Documents/AgenticAI/taparash/dist/taparash-0.3.0-py3-none-any.whl

# Test it
python -c "import taparash; print(f'Taparash v{taparash.__version__} installed successfully!')"

# Test functionality
python -c "
from taparash import TaparashFilter, QualityConfig
config = QualityConfig(enable_dlq=False)
app = TaparashFilter(config)
chunks = ['Valid text here', 'Short', 'Another valid chunk']
results = app.process_batch(chunks)
print(f'Processed: {results.total}, Accepted: {len(results.accepted)}, Rejected: {len(results.rejected)}')
print('SUCCESS!')
"
```

## 🐛 Why This Happens

Python's import system searches in this order:
1. Current directory (where you run python)
2. PYTHONPATH directories
3. Installed packages (site-packages)

Since there's a `taparash/` folder in the project directory, Python finds it first before checking the installed package!

## 🎯 For PyPI Publishing

Once you publish to PyPI, users won't have this problem because they'll install via:
```bash
pip install taparash
```

And they won't have a local `taparash/` directory to conflict with the installed package.

## ✅ Verification Commands

```bash
# Check where taparash is installed
pip show taparash

# Check what's being imported
python -c "import taparash; print(taparash.__file__)"

# Full functionality test
python -c "
from taparash import TaparashFilter, QualityConfig, DeadLetterQueue
from taparash.core import shannon_entropy, ExactDeduplicator
from taparash.profiler import TaparashProfiler
print('All imports successful!')
print('Taparash v0.3.0 is ready!')
"
```
