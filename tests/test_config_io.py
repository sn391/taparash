"""Tests for YAML/TOML config file loading and saving."""

import os
import tempfile
import pytest
from taparash import load_config, save_config, QualityConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_tmp(content: str, suffix: str) -> str:
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False, encoding="utf-8"
    )
    f.write(content)
    f.close()
    return f.name


def tmp_path(suffix: str) -> str:
    f = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    f.close()
    os.unlink(f.name)
    return f.name


# ---------------------------------------------------------------------------
# TOML loading
# ---------------------------------------------------------------------------

class TestLoadTOML:
    def test_basic_toml(self):
        path = write_tmp(
            'min_chunk_length = 10\nmax_chunk_length = 500\nenable_dlq = false\n',
            ".toml",
        )
        try:
            cfg = load_config(path)
            assert cfg.min_chunk_length == 10
            assert cfg.max_chunk_length == 500
            assert cfg.enable_dlq is False
        finally:
            os.unlink(path)

    def test_toml_defaults_for_unspecified_fields(self):
        path = write_tmp("min_chunk_length = 5\n", ".toml")
        try:
            cfg = load_config(path)
            # Unspecified fields retain QualityConfig defaults
            assert cfg.enable_pii_masking is True
            assert cfg.enable_exact_dedup is True
        finally:
            os.unlink(path)

    def test_toml_boolean_fields(self):
        path = write_tmp(
            "enable_pii_masking = false\npii_mask_iban = true\n", ".toml"
        )
        try:
            cfg = load_config(path)
            assert cfg.enable_pii_masking is False
            assert cfg.pii_mask_iban is True
        finally:
            os.unlink(path)

    def test_toml_float_fields(self):
        path = write_tmp("entropy_threshold = 3.8\ndedup_threshold = 0.75\n", ".toml")
        try:
            cfg = load_config(path)
            assert cfg.entropy_threshold == pytest.approx(3.8)
            assert cfg.dedup_threshold == pytest.approx(0.75)
        finally:
            os.unlink(path)

    def test_toml_unknown_key_raises(self):
        path = write_tmp("unknown_param = 42\n", ".toml")
        try:
            with pytest.raises(ValueError, match="Unknown config key"):
                load_config(path)
        finally:
            os.unlink(path)

    def test_toml_invalid_value_raises(self):
        # dedup_threshold must be 0.0–1.0
        path = write_tmp("dedup_threshold = 99.0\n", ".toml")
        try:
            with pytest.raises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# YAML loading
# ---------------------------------------------------------------------------

class TestLoadYAML:
    def test_basic_yaml(self):
        path = write_tmp(
            "min_chunk_length: 15\nmax_chunk_length: 1000\nenable_dlq: false\n",
            ".yaml",
        )
        try:
            cfg = load_config(path)
            assert cfg.min_chunk_length == 15
            assert cfg.max_chunk_length == 1000
            assert cfg.enable_dlq is False
        finally:
            os.unlink(path)

    def test_yml_extension_accepted(self):
        path = write_tmp("min_chunk_length: 25\n", ".yml")
        try:
            cfg = load_config(path)
            assert cfg.min_chunk_length == 25
        finally:
            os.unlink(path)

    def test_yaml_boolean_fields(self):
        path = write_tmp(
            "enable_fuzzy_dedup: false\npii_mask_eu_vat: true\n", ".yaml"
        )
        try:
            cfg = load_config(path)
            assert cfg.enable_fuzzy_dedup is False
            assert cfg.pii_mask_eu_vat is True
        finally:
            os.unlink(path)

    def test_yaml_unknown_key_raises(self):
        path = write_tmp("bogus_field: hello\n", ".yaml")
        try:
            with pytest.raises(ValueError, match="Unknown config key"):
                load_config(path)
        finally:
            os.unlink(path)

    def test_yaml_empty_file_returns_defaults(self):
        path = write_tmp("", ".yaml")
        try:
            cfg = load_config(path)
            assert isinstance(cfg, QualityConfig)
            assert cfg.min_chunk_length == 20  # default
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Unsupported format
# ---------------------------------------------------------------------------

def test_unsupported_extension_raises():
    with pytest.raises(ValueError, match="Unsupported config format"):
        load_config("pipeline.json")


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path/config.toml")


# ---------------------------------------------------------------------------
# save_config — TOML round-trip
# ---------------------------------------------------------------------------

class TestSaveTOML:
    def test_round_trip_toml(self):
        original = QualityConfig(
            min_chunk_length=5,
            max_chunk_length=500,
            enable_fuzzy_dedup=False,
            pii_mask_iban=True,
            enable_dlq=False,
        )
        path = tmp_path(".toml")
        try:
            save_config(original, path)
            restored = load_config(path)
            assert restored.min_chunk_length == 5
            assert restored.max_chunk_length == 500
            assert restored.enable_fuzzy_dedup is False
            assert restored.pii_mask_iban is True
            assert restored.enable_dlq is False
        finally:
            os.unlink(path)

    def test_toml_file_created(self):
        path = tmp_path(".toml")
        try:
            save_config(QualityConfig(enable_dlq=False), path)
            assert os.path.exists(path)
            content = open(path).read()
            assert "min_chunk_length" in content
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# save_config — YAML round-trip
# ---------------------------------------------------------------------------

class TestSaveYAML:
    def test_round_trip_yaml(self):
        original = QualityConfig(
            min_chunk_length=8,
            entropy_threshold=3.5,
            enable_pii_masking=False,
            pii_mask_eu_vat=True,
            enable_dlq=False,
        )
        path = tmp_path(".yaml")
        try:
            save_config(original, path)
            restored = load_config(path)
            assert restored.min_chunk_length == 8
            assert restored.entropy_threshold == pytest.approx(3.5)
            assert restored.enable_pii_masking is False
            assert restored.pii_mask_eu_vat is True
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# CLI --config flag
# ---------------------------------------------------------------------------

class TestCLIConfigFlag:
    def test_cli_loads_config_file(self):
        import io, json
        from taparash.cli import main

        cfg_path = write_tmp("min_chunk_length = 1\nenable_dlq = false\n", ".toml")
        stdin_text = json.dumps({"text": "ok"}) + "\n"

        old_stdin, old_stdout, old_argv = (
            __import__("sys").stdin,
            __import__("sys").stdout,
            __import__("sys").argv,
        )
        import sys
        sys.stdin = io.StringIO(stdin_text)
        out = io.StringIO()
        sys.stdout = out
        sys.argv = ["taparash", "filter", "-", "--config", cfg_path]
        exit_code = 0
        try:
            main()
        except SystemExit as e:
            exit_code = int(e.code or 0)
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout
            sys.argv = old_argv
            os.unlink(cfg_path)

        assert exit_code == 0
        lines = [l for l in out.getvalue().strip().split("\n") if l]
        # "ok" is only 2 chars; with default min=20 it would be rejected,
        # but the config file sets min_chunk_length=1 so it passes
        assert len(lines) == 1

    def test_cli_flag_overrides_config_file(self):
        import io, json
        from taparash.cli import main

        # Config file sets min=1 (would accept short text)
        cfg_path = write_tmp("min_chunk_length = 1\nenable_dlq = false\n", ".toml")
        stdin_text = json.dumps({"text": "ok"}) + "\n"

        import sys
        old_stdin, old_stdout, old_argv = sys.stdin, sys.stdout, sys.argv
        sys.stdin = io.StringIO(stdin_text)
        out = io.StringIO()
        sys.stdout = out
        # --min-length 100 overrides the config file value of 1
        sys.argv = ["taparash", "filter", "-", "--config", cfg_path, "--min-length", "100"]
        exit_code = 0
        try:
            main()
        except SystemExit as e:
            exit_code = int(e.code or 0)
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout
            sys.argv = old_argv
            os.unlink(cfg_path)

        assert exit_code == 0
        lines = [l for l in out.getvalue().strip().split("\n") if l]
        # "ok" is only 2 chars, --min-length 100 rejects it
        assert len(lines) == 0
