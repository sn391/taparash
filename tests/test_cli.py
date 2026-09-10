"""Tests for the taparash CLI (taparash_pkg/cli.py).

Uses the argparse interface directly — no subprocess overhead.
Stdout / stderr are captured with io.StringIO.
"""

import io
import json
import sys
import tempfile
import os
import pytest

from taparash.cli import _build_parser, main, _cmd_filter, _cmd_mask


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_cli(*argv, stdin_text: str = "") -> tuple:
    """Run the CLI with the given argv and return (stdout, stderr, exit_code)."""
    old_stdin = sys.stdin
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    old_argv = sys.argv

    sys.stdin = io.StringIO(stdin_text)
    out = io.StringIO()
    err = io.StringIO()
    sys.stdout = out
    sys.stderr = err
    sys.argv = ["taparash", *argv]

    exit_code = 0
    try:
        main()
    except SystemExit as e:
        exit_code = int(e.code) if e.code is not None else 0
    finally:
        sys.stdin = old_stdin
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        sys.argv = old_argv

    return out.getvalue(), err.getvalue(), exit_code


def make_jsonl(*texts) -> str:
    return "\n".join(json.dumps({"text": t}) for t in texts) + "\n"


def make_txt(*texts) -> str:
    return "\n".join(texts) + "\n"


# ---------------------------------------------------------------------------
# version command
# ---------------------------------------------------------------------------

def test_version_command():
    stdout, _, code = run_cli("version")
    assert code == 0
    assert "taparash" in stdout


# ---------------------------------------------------------------------------
# filter — basic I/O
# ---------------------------------------------------------------------------

def test_filter_stdin_stdout_jsonl():
    chunks = [
        "This is a clean and valid text chunk for the pipeline test.",
        "Another valid piece of content that should pass all gates.",
    ]
    stdin = make_jsonl(*chunks)
    stdout, _, code = run_cli("filter", "-", "--no-dlq", stdin_text=stdin)
    assert code == 0
    lines = [l for l in stdout.strip().split("\n") if l]
    assert len(lines) == 2
    for line in lines:
        obj = json.loads(line)
        assert "text" in obj


def test_filter_txt_format():
    stdin = make_txt(
        "Valid text chunk that is definitely long enough to pass the filter.",
        "Another valid line for the test pipeline run here.",
    )
    stdout, _, code = run_cli(
        "filter", "-", "--format", "txt", "--no-dlq", stdin_text=stdin
    )
    assert code == 0
    lines = [l for l in stdout.strip().split("\n") if l]
    assert len(lines) == 2


def test_filter_rejects_short_chunks():
    stdin = make_jsonl("Too short.", "This line is long enough to make it through the length gate.")
    stdout, _, code = run_cli("filter", "-", "--no-dlq", stdin_text=stdin)
    assert code == 0
    lines = [l for l in stdout.strip().split("\n") if l]
    assert len(lines) == 1
    assert "long enough" in json.loads(lines[0])["text"]


def test_filter_min_length_override():
    stdin = make_jsonl("ok")  # 2 chars — rejected by default (min=20), pass with min=1
    stdout, _, code = run_cli(
        "filter", "-", "--min-length", "1", "--no-dlq", stdin_text=stdin
    )
    assert code == 0
    lines = [l for l in stdout.strip().split("\n") if l]
    assert len(lines) == 1


def test_filter_deduplication():
    text = "This is an exact duplicate sentence for testing the dedup gate here."
    stdin = make_jsonl(text, text)
    stdout, _, code = run_cli("filter", "-", "--no-dlq", stdin_text=stdin)
    assert code == 0
    lines = [l for l in stdout.strip().split("\n") if l]
    assert len(lines) == 1


def test_filter_no_dedup_flag():
    text = "This is an exact duplicate sentence for testing the dedup gate here."
    stdin = make_jsonl(text, text)
    stdout, _, code = run_cli("filter", "-", "--no-dedup", "--no-dlq", stdin_text=stdin)
    assert code == 0
    lines = [l for l in stdout.strip().split("\n") if l]
    assert len(lines) == 2  # both pass when dedup disabled


def test_filter_custom_text_field():
    record = json.dumps({"content": "This is a valid piece of content for the test pipeline."})
    stdin = record + "\n"
    stdout, _, code = run_cli(
        "filter", "-", "--text-field", "content", "--no-dlq", stdin_text=stdin
    )
    assert code == 0
    lines = [l for l in stdout.strip().split("\n") if l]
    assert len(lines) == 1
    assert "content" in json.loads(lines[0])


def test_filter_stats_output():
    stdin = make_jsonl(
        "Valid content that passes all quality gates in the pipeline.",
        "x",  # too short → rejected
    )
    _, stderr, code = run_cli("filter", "-", "--no-dlq", "--stats", stdin_text=stdin)
    assert code == 0
    assert "Processed:" in stderr
    assert "Accepted:" in stderr


def test_filter_rejected_file():
    short = "x"
    valid = "This valid text should pass all the quality gates easily."
    stdin = make_jsonl(short, valid)
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as rej_f:
        rej_path = rej_f.name

    try:
        stdout, _, code = run_cli(
            "filter", "-", "--rejected", rej_path, "--no-dlq", stdin_text=stdin
        )
        assert code == 0
        with open(rej_path, encoding="utf-8") as f:
            rej_lines = [l for l in f.read().strip().split("\n") if l]
        assert len(rej_lines) == 1
        rej_obj = json.loads(rej_lines[0])
        assert "_taparash_reason" in rej_obj
    finally:
        os.unlink(rej_path)


def test_filter_output_to_file():
    stdin = make_jsonl("This is valid content that passes all the quality gates.")
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as out_f:
        out_path = out_f.name

    try:
        _, _, code = run_cli(
            "filter", "-", out_path, "--no-dlq", stdin_text=stdin
        )
        assert code == 0
        with open(out_path, encoding="utf-8") as f:
            lines = [l for l in f.read().strip().split("\n") if l]
        assert len(lines) == 1
    finally:
        os.unlink(out_path)


# ---------------------------------------------------------------------------
# filter — European PII flags
# ---------------------------------------------------------------------------

def test_filter_pii_iban_flag():
    stdin = make_jsonl(
        "Wire transfer to GB29NWBK60161331926819 must arrive by end of day."
    )
    stdout, _, code = run_cli(
        "filter", "-", "--pii-iban", "--no-dlq", "--no-entropy", stdin_text=stdin
    )
    assert code == 0
    lines = [l for l in stdout.strip().split("\n") if l]
    assert len(lines) == 1
    assert "GB29NWBK60161331926819" not in json.loads(lines[0])["text"]


def test_filter_pii_eu_vat_flag():
    stdin = make_jsonl("Supplier VAT number is DE123456789 per the invoice.")
    stdout, _, code = run_cli(
        "filter", "-", "--pii-eu-vat", "--no-dlq", "--no-entropy", stdin_text=stdin
    )
    assert code == 0
    lines = [l for l in stdout.strip().split("\n") if l]
    assert len(lines) == 1
    assert "DE123456789" not in json.loads(lines[0])["text"]


# ---------------------------------------------------------------------------
# mask command
# ---------------------------------------------------------------------------

def test_mask_command_basic():
    stdin = make_txt("Contact us at secret@example.com for more details here.")
    stdout, _, code = run_cli("mask", "-", "--format", "txt", stdin_text=stdin)
    assert code == 0
    assert "secret@example.com" not in stdout
    assert "[REDACTED]" in stdout


def test_mask_command_stats():
    stdin = make_txt("Email admin@test.org or call +1-800-555-0100 for support.")
    _, stderr, code = run_cli("mask", "-", "--format", "txt", "--stats", stdin_text=stdin)
    assert code == 0
    assert "PII hits:" in stderr


def test_mask_pii_iban_opt_in():
    stdin = make_txt("Account GB29NWBK60161331926819 is the destination.")
    # With --pii-iban: full IBAN replaced as a single [REDACTED] token
    stdout_yes, _, _ = run_cli(
        "mask", "-", "--format", "txt", "--pii-iban", stdin_text=stdin
    )
    assert "GB29NWBK60161331926819" not in stdout_yes
    assert "[REDACTED]" in stdout_yes
    # The IBAN pattern fires before the phone sub-match, so only one token appears
    assert stdout_yes.count("[REDACTED]") == 1


# ---------------------------------------------------------------------------
# help / parser smoke tests
# ---------------------------------------------------------------------------

def test_help_does_not_crash():
    parser = _build_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--help"])
    assert exc_info.value.code == 0


def test_filter_help_does_not_crash():
    parser = _build_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["filter", "--help"])
    assert exc_info.value.code == 0
