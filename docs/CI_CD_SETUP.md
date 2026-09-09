# CI/CD Setup Guide

This guide explains how to set up and use the Continuous Integration and Continuous Deployment (CI/CD) pipeline for Taparash.

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Workflows](#workflows)
- [Secrets Configuration](#secrets-configuration)
- [Branch Protection](#branch-protection)
- [Local Testing](#local-testing)
- [Troubleshooting](#troubleshooting)

---

## Overview

Taparash uses GitHub Actions for automated:
- ✅ Testing across multiple Python versions and operating systems
- 🔍 Code quality checks (linting, formatting, security)
- 📦 Package building and validation
- 🚀 Publishing to PyPI
- 🔄 Dependency monitoring

---

## Prerequisites

1. **GitHub Repository**: Push your code to GitHub
2. **PyPI Account**: Create account at https://pypi.org
3. **PyPI API Token**: Generate at https://pypi.org/manage/account/token/

---

## Initial Setup

### 1. Push Workflows to GitHub

```bash
cd C:/Users/sn391/Documents/AgenticAI/taparash
git add .github/
git commit -m "ci: Add CI/CD workflows with GitHub Actions"
git push origin main
```

### 2. Configure PyPI Token

#### Step 1: Create PyPI Token
1. Go to https://pypi.org/manage/account/token/
2. Click "Add API token"
3. Name: `taparash-github-actions`
4. Scope: "Project: taparash" (after first manual upload) or "Entire account"
5. **Copy the token** (starts with `pypi-`)

#### Step 2: Add to GitHub Secrets
1. Go to: `https://github.com/sn391/taparash/settings/secrets/actions`
2. Click "New repository secret"
3. Name: `PYPI_API_TOKEN`
4. Value: Paste your token
5. Click "Add secret"

### 3. Optional: Configure Codecov (for coverage reports)

1. Go to: https://codecov.io/
2. Sign in with GitHub
3. Add repository: `sn391/taparash`
4. Copy upload token
5. Add to GitHub Secrets:
   - Name: `CODECOV_TOKEN`
   - Value: Your Codecov token

---

## Workflows

### 🧪 Tests Workflow
**File**: `.github/workflows/tests.yml`
**Trigger**: Push, PR, Manual

**What it tests:**
- Python 3.9, 3.10, 3.11, 3.12
- Ubuntu, Windows, macOS
- With and without optional dependencies
- Generates coverage reports

**View results**: https://github.com/sn391/taparash/actions/workflows/tests.yml

---

### 🔍 Code Quality Workflow
**File**: `.github/workflows/code-quality.yml`
**Trigger**: Push, PR, Manual

**Checks:**
- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Code linting
- **mypy**: Type checking
- **bandit**: Security vulnerabilities

**View results**: https://github.com/sn391/taparash/actions/workflows/code-quality.yml

---

### 📦 Build Workflow
**File**: `.github/workflows/build.yml`
**Trigger**: Push, PR, Release, Manual

**Actions:**
- Builds wheel and source distribution
- Validates with twine
- Tests installation on all platforms
- Uploads artifacts

**View results**: https://github.com/sn391/taparash/actions/workflows/build.yml

---

### 🚀 Publish Workflow
**File**: `.github/workflows/publish.yml`
**Trigger**: GitHub Release, Manual

**Actions:**
- Builds package
- Publishes to PyPI
- Attaches files to release

**View results**: https://github.com/sn391/taparash/actions/workflows/publish.yml

---

### 🔄 Dependencies Workflow
**File**: `.github/workflows/dependencies.yml`
**Trigger**: Weekly (Sundays), Manual

**Actions:**
- Checks for outdated packages
- Runs security audit
- Reports vulnerabilities

**View results**: https://github.com/sn391/taparash/actions/workflows/dependencies.yml

---

## Secrets Configuration

### Required Secrets

| Secret Name | Required For | How to Get |
|-------------|--------------|------------|
| `PYPI_API_TOKEN` | Publishing to PyPI | https://pypi.org/manage/account/token/ |

### Optional Secrets

| Secret Name | Purpose | How to Get |
|-------------|---------|------------|
| `TEST_PYPI_API_TOKEN` | Publishing to TestPyPI | https://test.pypi.org/manage/account/token/ |
| `CODECOV_TOKEN` | Coverage reports | https://codecov.io/ |

---

## Branch Protection

Protect your `main` branch from accidental changes:

### Setup Instructions

1. Go to: `https://github.com/sn391/taparash/settings/branches`
2. Click "Add rule"
3. Branch name pattern: `main`
4. Enable these settings:

#### Required Status Checks
- ✅ Require status checks to pass before merging
- ✅ Require branches to be up to date before merging
- Select required checks:
  - ✅ Test Python 3.12 on ubuntu-latest
  - ✅ Lint and Format Check
  - ✅ Build Distribution

#### Pull Request Requirements
- ✅ Require a pull request before merging
- ✅ Require approvals: 1
- ✅ Dismiss stale pull request approvals when new commits are pushed

#### Other Settings
- ✅ Require linear history
- ✅ Do not allow bypassing the above settings

---

## Local Testing

Run the same checks locally before pushing:

### Install Development Dependencies

```bash
pip install -e .[dev]
pip install black isort flake8 mypy bandit pytest-cov
```

### Run Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=taparash_pkg --cov-report=html
```

### Check Code Quality

```bash
# Format code
black taparash_pkg/ tests/

# Sort imports
isort taparash_pkg/ tests/

# Lint code
flake8 taparash_pkg/ tests/ --max-line-length=100

# Type check
mypy taparash_pkg/ --ignore-missing-imports

# Security scan
bandit -r taparash_pkg/
```

### Build Package

```bash
# Clean old builds
rm -rf dist/ build/ *.egg-info

# Build
python -m build

# Validate
twine check dist/*
```

---

## Troubleshooting

### Tests Failing on CI but Passing Locally

**Possible causes:**
- Environment differences (OS, Python version)
- Missing dependencies
- Timezone/locale issues
- File path issues (Windows vs Unix)

**Solutions:**
- Check workflow logs for specific errors
- Run tests locally with the same Python version
- Test on Docker with Ubuntu image
- Check for hardcoded paths

---

### Code Quality Checks Failing

**Black formatting issues:**
```bash
# Fix automatically
black taparash_pkg/ tests/
```

**isort import issues:**
```bash
# Fix automatically
isort taparash_pkg/ tests/
```

**flake8 issues:**
- Read error messages and fix manually
- Some can be ignored with `# noqa` comments

---

### Build Failing

**Common issues:**
1. **Missing files**: Check `MANIFEST.in`
2. **Version conflicts**: Update `pyproject.toml`
3. **Import errors**: Check package structure

**Debug steps:**
```bash
# List what's in the wheel
unzip -l dist/*.whl

# List what's in the tarball
tar -tzf dist/*.tar.gz
```

---

### Publish Failing

**Error: "File already exists"**
- PyPI doesn't allow re-uploading same version
- Solution: Increment version in `pyproject.toml`

**Error: "Invalid credentials"**
- Check `PYPI_API_TOKEN` secret is set correctly
- Ensure username is `__token__` (not your username)

**Error: "Package name already taken"**
- Someone else owns that name
- Solution: Choose different name

---

## Manual Workflow Triggers

Trigger any workflow manually:

1. Go to: https://github.com/sn391/taparash/actions
2. Select the workflow
3. Click "Run workflow" button
4. Select branch
5. Fill in inputs (if any)
6. Click "Run workflow"

### Example: Manual Publish

1. Go to "Publish to PyPI" workflow
2. Click "Run workflow"
3. Select environment: `pypi` or `testpypi`
4. Click "Run workflow"

---

## Monitoring

### Check Workflow Status

- **All workflows**: https://github.com/sn391/taparash/actions
- **Specific workflow**: Click on workflow name
- **Failed runs**: Filter by "Status: Failure"

### Email Notifications

GitHub automatically emails you when:
- Workflow fails
- Workflow succeeds after failures
- First time a workflow runs

Configure at: https://github.com/settings/notifications

---

## Best Practices

### Before Committing

1. ✅ Run tests locally: `pytest tests/`
2. ✅ Format code: `black taparash_pkg/ tests/`
3. ✅ Sort imports: `isort taparash_pkg/ tests/`
4. ✅ Check linting: `flake8 taparash_pkg/ tests/`

### Creating Pull Requests

1. ✅ Create feature branch: `git checkout -b feature/my-feature`
2. ✅ Make changes and commit
3. ✅ Push to GitHub: `git push origin feature/my-feature`
4. ✅ Create PR from branch
5. ✅ Wait for CI checks to pass
6. ✅ Request review

### Releasing New Version

1. ✅ Update version in `pyproject.toml`
2. ✅ Update `CHANGELOG.md`
3. ✅ Commit: `git commit -m "chore: bump version to 0.3.1"`
4. ✅ Create tag: `git tag -a v0.3.1 -m "Release v0.3.1"`
5. ✅ Push: `git push origin main --tags`
6. ✅ Create GitHub Release
7. ✅ Publish workflow runs automatically

---

## Advanced Configuration

### Custom Matrix Testing

Edit `.github/workflows/tests.yml`:

```yaml
strategy:
  matrix:
    python-version: ["3.9", "3.10", "3.11", "3.12", "3.13"]
    os: [ubuntu-latest, ubuntu-20.04, windows-latest, macos-latest]
```

### Speed Up CI

**Use caching:**
```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
    cache: 'pip'  # Caches pip packages
```

**Parallel jobs:**
- Already configured with matrix strategy
- Each combination runs in parallel

---

## Resources

- **GitHub Actions Docs**: https://docs.github.com/en/actions
- **PyPI Publishing Guide**: https://packaging.python.org/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/
- **Codecov Docs**: https://docs.codecov.com/docs
- **Python Packaging**: https://packaging.python.org/

---

**Last Updated**: 2026-09-09
**Maintainer**: @sn391
