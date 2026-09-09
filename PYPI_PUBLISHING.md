# PyPI Publishing Guide for Taparash

This guide covers how to build and publish Taparash to PyPI.

## Prerequisites

### 1. Install Build Tools

```bash
pip install --upgrade pip
pip install build twine
```

### 2. PyPI Account Setup

- Create account at https://pypi.org
- Create account at https://test.pypi.org (for testing)
- Generate API tokens:
  - Go to Account Settings → API tokens
  - Create token for project upload

## Pre-Publishing Checklist

### 1. Version Check

Ensure version is correct in:
- `taparash/__init__.py` → `__version__ = "0.1.0"`
- `pyproject.toml` → `version = "0.1.0"`

### 2. Documentation Review

- [ ] README.md is complete and accurate
- [ ] All examples work correctly
- [ ] Installation instructions are clear
- [ ] Dependencies are properly listed

### 3. Code Quality

```bash
# Run tests
cd C:\Users\sn391\Documents\AgenticAI
python taparash/test_pipeline.py
python taparash/test_pr2_features.py

# Format code (optional)
black taparash/
isort taparash/

# Type check (optional)
mypy taparash/
```

### 4. Clean Build Environment

```bash
cd C:\Users\sn391\Documents\AgenticAI\taparash

# Remove old builds
rm -rf build/ dist/ *.egg-info

# Remove Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

## Building the Package

### 1. Build Distribution Files

```bash
cd C:\Users\sn391\Documents\AgenticAI\taparash

# Build source distribution and wheel
python -m build
```

This creates:
- `dist/taparash-0.1.0.tar.gz` (source distribution)
- `dist/taparash-0.1.0-py3-none-any.whl` (wheel)

### 2. Verify Package Contents

```bash
# Check what's included
tar -tzf dist/taparash-0.1.0.tar.gz | head -20

# Or for wheel
unzip -l dist/taparash-0.1.0-py3-none-any.whl | head -20
```

### 3. Verify Package Metadata

```bash
twine check dist/*
```

Should show: `PASSED` for all files.

## Testing on Test PyPI (Recommended)

### 1. Upload to Test PyPI

```bash
twine upload --repository testpypi dist/*
```

Enter your Test PyPI credentials or API token:
- Username: `__token__`
- Password: `pypi-...` (your API token)

### 2. Test Installation

```bash
# Create fresh virtual environment
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate

# Install from Test PyPI
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            taparash

# Test it works
python -c "from taparash import TaparashFilter, QualityConfig; print('OK')"

# Deactivate and remove
deactivate
rm -rf test_env
```

## Publishing to PyPI

### 1. Upload to PyPI

```bash
cd C:\Users\sn391\Documents\AgenticAI\taparash

twine upload dist/*
```

Enter your PyPI credentials or API token:
- Username: `__token__`
- Password: `pypi-...` (your API token)

### 2. Verify on PyPI

Visit: https://pypi.org/project/taparash/

Check:
- Package page loads correctly
- README renders properly
- Links work (GitHub, documentation)
- Dependencies are correct

### 3. Test Installation

```bash
# Fresh environment
python -m venv verify_env
source verify_env/bin/activate  # On Windows: verify_env\Scripts\activate

# Install from PyPI
pip install taparash

# Test basic functionality
python -c "
from taparash import TaparashFilter, QualityConfig
config = QualityConfig()
app = TaparashFilter(config)
print('Taparash installed successfully!')
"

# Test with optional dependencies
pip install taparash[semantic]
python -c "from taparash.engines import LocalEmbedder; print('Semantic features available!')"

# Cleanup
deactivate
rm -rf verify_env
```

## Installation Methods for Users

### Basic Installation (Core Features)

```bash
pip install taparash
```

Includes:
- Length validation
- PII masking
- Entropy filtering
- Exact & fuzzy deduplication
- Dead Letter Queue

### With Semantic Features

```bash
pip install taparash[semantic]
```

Additional features:
- Local embeddings
- Semantic deduplication
- Vector similarity

### All Features

```bash
pip install taparash[all]
```

### Development Installation

```bash
pip install taparash[dev]
```

Includes testing and linting tools.

## Updating Package

### For New Release

1. **Update version** in:
   - `taparash/__init__.py`
   - `pyproject.toml`

2. **Update CHANGELOG** (create if needed)

3. **Tag release** in git:
   ```bash
   git tag -a v0.1.0 -m "Release v0.1.0"
   git push origin v0.1.0
   ```

4. **Rebuild and upload**:
   ```bash
   rm -rf dist/
   python -m build
   twine check dist/*
   twine upload dist/*
   ```

## Configuration with API Token

### Save Token (Recommended)

Create `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmc...YOUR_TOKEN_HERE

[testpypi]
username = __token__
password = pypi-AgENdGVzdC5weXBpLm9yZw...YOUR_TOKEN_HERE
```

Then upload with:
```bash
twine upload dist/*
```

## Troubleshooting

### Issue: Package Already Exists

**Error:** `File already exists`

**Solution:** 
- You cannot re-upload same version
- Increment version number
- Delete old dist/ files

### Issue: Invalid Package Structure

**Error:** `Invalid distribution` or `cannot find module`

**Solution:**
- Check `pyproject.toml` packages list
- Verify `__init__.py` exists in all packages
- Rebuild: `rm -rf dist/ && python -m build`

### Issue: Dependencies Not Installing

**Error:** Users report missing dependencies

**Solution:**
- Check `dependencies` in `pyproject.toml`
- Test fresh install in clean environment
- Ensure numpy is in core dependencies

### Issue: README Not Rendering

**Error:** PyPI page shows raw markdown

**Solution:**
- Verify `readme = "README.md"` in `pyproject.toml`
- Check README.md is in MANIFEST.in
- Ensure UTF-8 encoding

## Best Practices

1. **Test on Test PyPI first** - Always test upload flow
2. **Use API tokens** - More secure than passwords
3. **Tag releases in Git** - Track versions
4. **Write changelog** - Help users understand updates
5. **Semantic versioning** - MAJOR.MINOR.PATCH
6. **Clean builds** - Delete dist/ before rebuilding
7. **Verify metadata** - Run `twine check` always

## Version Guidelines

- **0.1.0** - Initial release with PR1 + PR2 features
- **0.2.0** - Adding PR3 (NLI) features
- **1.0.0** - Production-ready, stable API
- **1.1.0** - New features (backward compatible)
- **2.0.0** - Breaking changes

## Post-Publication

1. **Update README badge** with PyPI link
2. **Create GitHub release** with notes
3. **Announce** on relevant channels
4. **Monitor** PyPI download stats
5. **Respond** to issues and questions

## Quick Reference

```bash
# Complete publishing workflow
cd C:\Users\sn391\Documents\AgenticAI\taparash

# Clean
rm -rf dist/ build/ *.egg-info

# Build
python -m build

# Check
twine check dist/*

# Test upload
twine upload --repository testpypi dist/*

# Production upload
twine upload dist/*
```

## Resources

- PyPI: https://pypi.org
- Test PyPI: https://test.pypi.org
- Packaging Guide: https://packaging.python.org
- Twine Documentation: https://twine.readthedocs.io
- Build Documentation: https://build.pypa.io
