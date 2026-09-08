# Taparash Project Guidelines

## Core Rules
- **Zero-LLM & 100% Offline:** No external API calls, no generative LLMs.
- **Python Version:** 3.9+
- **Code Style:** PEP8, Type Hints on all functions, explicit docstrings.
- **Architecture:** Pure functions for core logic, low-overhead algorithms.

## Module Structure
- `src/taparash/core/`: Entropy, Hash Deduplication, PII Masking
- `src/taparash/engines/`: Local MiniLM, Local Cross-Encoder
- `tests/`: Pytest files for every module

## Commands
- Build/Install: `pip install -e .`
- Run Tests: `pytest tests/`
- Type Check: `mypy src/`