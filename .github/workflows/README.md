# GitHub Actions CI/CD Workflows

This directory contains automated workflows for testing, building, and deploying the Taparash package.

## Workflows Overview

### 🧪 **tests.yml** - Automated Testing
**Triggers:** Push to main/develop, Pull Requests, Manual

**What it does:**
- Tests on multiple Python versions (3.9, 3.10, 3.11, 3.12)
- Tests on multiple operating systems (Ubuntu, Windows, macOS)
- Runs core tests without optional dependencies
- Runs full test suite with all optional dependencies
- Generates code coverage reports
- Uploads coverage to Codecov

**Matrix:**
- OS: Ubuntu, Windows, macOS
- Python: 3.9, 3.10, 3.11, 3.12

---

### 🔍 **code-quality.yml** - Code Quality Checks
**Triggers:** Push to main/develop, Pull Requests, Manual

**What it does:**
- **Formatting:** Checks code formatting with Black
- **Import Sorting:** Validates import order with isort
- **Linting:** Analyzes code with flake8
- **Type Checking:** Validates types with mypy
- **Security:** Scans for vulnerabilities with bandit

---

### 📦 **build.yml** - Package Building
**Triggers:** Push, Pull Requests, Releases, Manual

**What it does:**
- Builds wheel and source distributions
- Validates package with twine check
- Tests installation on multiple platforms
- Verifies basic functionality
- Uploads build artifacts

---

### 🚀 **publish.yml** - PyPI Publishing
**Triggers:** GitHub Releases, Manual

**What it does:**
- Builds package for release
- Publishes to PyPI on release
- Can manually publish to TestPyPI
- Attaches distributions to GitHub release

**Required Secrets:**
- `PYPI_API_TOKEN` - Your PyPI API token
- `TEST_PYPI_API_TOKEN` - Your TestPyPI token (optional)

---

### 🔄 **dependencies.yml** - Dependency Monitoring
**Triggers:** Weekly (Sundays), Manual

**What it does:**
- Checks for outdated dependencies
- Runs security audit with pip-audit
- Reports vulnerabilities

---

### 🤖 **dependabot.yml** - Automated Updates
**Configuration file for GitHub Dependabot**

**What it does:**
- Automatically creates PRs for dependency updates
- Updates Python packages weekly
- Updates GitHub Actions weekly
- Keeps dependencies secure and up-to-date

---

## Setup Instructions

### 1. Enable GitHub Actions
GitHub Actions are enabled by default. Push these workflows to trigger them.

### 2. Add PyPI Token (for publishing)
1. Go to: https://pypi.org/manage/account/token/
2. Create a token with scope for "taparash"
3. Add to GitHub Secrets:
   - Go to: `Settings` → `Secrets and variables` → `Actions`
   - Click `New repository secret`
   - Name: `PYPI_API_TOKEN`
   - Value: Your token

### 3. Add Codecov Token (optional)
1. Go to: https://codecov.io/
2. Sign in with GitHub
3. Add your repository
4. Copy the token
5. Add to GitHub Secrets as `CODECOV_TOKEN`

### 4. Configure Branch Protection (recommended)
1. Go to: `Settings` → `Branches`
2. Add rule for `main` branch
3. Enable:
   - ✅ Require status checks to pass
   - ✅ Require branches to be up to date
   - Select: `Test`, `Lint`, `Build`
   - ✅ Require pull request reviews

---

## Workflow Status Badges

Add these badges to your README.md:

```markdown
[![Tests](https://github.com/sn391/taparash/actions/workflows/tests.yml/badge.svg)](https://github.com/sn391/taparash/actions/workflows/tests.yml)
[![Code Quality](https://github.com/sn391/taparash/actions/workflows/code-quality.yml/badge.svg)](https://github.com/sn391/taparash/actions/workflows/code-quality.yml)
[![Build](https://github.com/sn391/taparash/actions/workflows/build.yml/badge.svg)](https://github.com/sn391/taparash/actions/workflows/build.yml)
[![codecov](https://codecov.io/gh/sn391/taparash/branch/main/graph/badge.svg)](https://codecov.io/gh/sn391/taparash)
```

---

## Manual Workflow Triggers

All workflows can be triggered manually:

1. Go to: `Actions` tab
2. Select the workflow
3. Click `Run workflow`
4. Choose branch and options

---

## Troubleshooting

### Tests Failing
- Check Python version compatibility
- Verify all dependencies are installed
- Check for platform-specific issues

### Build Failing
- Ensure `pyproject.toml` is correct
- Check that all files are included
- Verify `MANIFEST.in` if used

### Publish Failing
- Verify `PYPI_API_TOKEN` is set correctly
- Ensure version number is unique
- Check package name isn't already taken

### Code Quality Warnings
- Run `black taparash_pkg/` locally to fix formatting
- Run `isort taparash_pkg/` to fix imports
- Address flake8 issues

---

## Local Testing

Run the same checks locally before pushing:

```bash
# Run tests
pytest tests/ -v

# Check formatting
black --check taparash_pkg/ tests/

# Check imports
isort --check-only taparash_pkg/ tests/

# Lint code
flake8 taparash_pkg/ tests/

# Type check
mypy taparash_pkg/

# Build package
python -m build
twine check dist/*
```

---

## Continuous Improvement

These workflows are living documents. Feel free to:
- Add more test cases
- Adjust Python versions
- Add performance benchmarks
- Include additional linters
- Customize triggers

**Last Updated:** 2026-09-09
