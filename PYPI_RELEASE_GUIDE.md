# PyPI Release Guide for Taparash v0.3.0

## ✅ Pre-Release Checklist

All items below are **COMPLETE** and ready for release:

- [x] All Phase 1, 2, 3 features implemented
- [x] Version updated to 0.3.0 in:
  - [x] `pyproject.toml`
  - [x] `__init__.py`
  - [x] `README.md`
- [x] `CHANGELOG.md` created and updated
- [x] `LICENSE` file (MIT)
- [x] `README.md` comprehensive documentation
- [x] `MANIFEST.in` configured
- [x] Package structure correct
- [x] Tests written and passing
- [x] Dependencies declared in `pyproject.toml`

---

## 📦 Steps to Publish to PyPI

### Step 1: Install Build Tools

```bash
pip install --upgrade pip
pip install --upgrade build twine
```

### Step 2: Clean Previous Builds

```bash
# Remove old distribution files
rm -rf dist/
rm -rf build/
rm -rf *.egg-info
```

On Windows:
```cmd
rmdir /s /q dist
rmdir /s /q build
rmdir /s /q taparash.egg-info
```

### Step 3: Build the Package

```bash
python -m build
```

This creates:
- `dist/taparash-0.3.0-py3-none-any.whl` (wheel)
- `dist/taparash-0.3.0.tar.gz` (source distribution)

### Step 4: Check the Package

```bash
twine check dist/*
```

Expected output:
```
Checking dist/taparash-0.3.0-py3-none-any.whl: PASSED
Checking dist/taparash-0.3.0.tar.gz: PASSED
```

### Step 5: Test Install Locally

```bash
# Create a test virtual environment
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate

# Install from the built wheel
pip install dist/taparash-0.3.0-py3-none-any.whl

# Test the installation
python -c "import taparash; print(f'Taparash v{taparash.__version__} installed successfully!')"
python -c "from taparash import TaparashFilter, QualityConfig; print('Core imports work!')"

# Deactivate and remove test environment
deactivate
rm -rf test_env  # On Windows: rmdir /s /q test_env
```

### Step 6A: Upload to TestPyPI (Recommended First)

```bash
# Upload to TestPyPI for testing
twine upload --repository testpypi dist/*
```

You'll be prompted for:
- **Username:** `__token__`
- **Password:** Your TestPyPI API token

Then test installation from TestPyPI:
```bash
pip install --index-url https://test.pypi.org/simple/ taparash
```

### Step 6B: Upload to PyPI (Production)

```bash
# Upload to PyPI
twine upload dist/*
```

You'll be prompted for:
- **Username:** `__token__`
- **Password:** Your PyPI API token

---

## 🔑 Setting Up PyPI API Tokens

### Create PyPI Account
1. Go to https://pypi.org/
2. Register a new account
3. Verify your email

### Create API Token
1. Go to https://pypi.org/manage/account/token/
2. Click "Add API token"
3. Name: "taparash-upload"
4. Scope: "Entire account" (or specific to taparash project after first upload)
5. Copy the token (starts with `pypi-`)
6. **Save it securely** - you can't view it again!

### For TestPyPI (Optional but Recommended)
1. Go to https://test.pypi.org/
2. Register a separate account
3. Create API token at https://test.pypi.org/manage/account/token/

### Store Tokens Securely

Option 1: Use `.pypirc` file
```bash
# Create ~/.pypirc (Linux/Mac) or %USERPROFILE%\.pypirc (Windows)
cat > ~/.pypirc << EOF
[pypi]
username = __token__
password = pypi-YOUR_TOKEN_HERE

[testpypi]
username = __token__
password = pypi-YOUR_TESTPYPI_TOKEN_HERE
EOF

# Secure the file
chmod 600 ~/.pypirc
```

Option 2: Use environment variables
```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-YOUR_TOKEN_HERE
```

---

## 📋 Post-Release Checklist

After successful upload to PyPI:

- [ ] Test installation: `pip install taparash`
- [ ] Verify on PyPI: https://pypi.org/project/taparash/
- [ ] Create GitHub release (v0.3.0)
- [ ] Tag the commit: `git tag -a v0.3.0 -m "Release v0.3.0"`
- [ ] Push tags: `git push origin v0.3.0`
- [ ] Update project status in README if needed
- [ ] Announce release (Twitter, Reddit, etc.)

---

## 🐛 Troubleshooting

### "File already exists" Error

If you get an error about files already existing:
- PyPI doesn't allow overwriting versions
- You must increment the version number
- Delete and re-upload only works on TestPyPI

### Import Errors After Install

If imports fail after `pip install taparash`:
```bash
# Check what was installed
pip show taparash
pip show -f taparash

# Verify package contents
python -c "import taparash; print(taparash.__file__)"
python -c "import taparash; print(dir(taparash))"
```

### Missing Dependencies

If sentence-transformers is required but not installed:
```bash
# Install with semantic features
pip install taparash[semantic]

# Or install all optional dependencies
pip install taparash[all]
```

---

## 🎯 Quick Release Commands (Copy-Paste)

```bash
# Full release workflow
rm -rf dist/ build/ *.egg-info
python -m build
twine check dist/*
twine upload --repository testpypi dist/*  # Test first
twine upload dist/*                         # Then production

# Verify
pip install taparash
python -c "import taparash; print(f'v{taparash.__version__}')"
```

---

## 📊 Package Statistics

### Current Release: v0.3.0

**Lines of Code:**
- Phase 1: ~800 lines
- Phase 2: ~900 lines  
- Phase 3: ~800 lines
- **Total:** ~2,500 lines of production code

**Features:**
- 7 processing gates
- 3 deduplication methods
- 2 ML models (optional)
- Performance profiling
- Dead letter queue
- Full offline operation

**Dependencies:**
- Core: numpy only
- Optional: sentence-transformers, torch

---

## 🔄 Future Releases

### Versioning Strategy

- **Patch releases (0.3.x):** Bug fixes, documentation updates
- **Minor releases (0.x.0):** New features, backwards compatible
- **Major releases (x.0.0):** Breaking changes

### Release Cadence

- **Bug fixes:** As needed
- **Feature releases:** When complete and tested
- **Major versions:** Quarterly or as needed

---

## 📞 Support

- **Issues:** https://github.com/sn391/taparash/issues
- **PyPI Page:** https://pypi.org/project/taparash/
- **Email:** sn391@yahoo.com

---

## ✨ First Release Celebration!

Once v0.3.0 is live on PyPI, anyone worldwide can install it with:

```bash
pip install taparash
```

That's the magic of open source! 🎉
