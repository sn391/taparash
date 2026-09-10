"""Taparash command-line interface.

Entry point: taparash <command> [options]

Commands
--------
filter   Filter text chunks through the quality pipeline.
mask     Apply PII masking only (no dedup / entropy / length checks).
version  Print version and exit.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import IO, Iterator, Tuple


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="taparash",
        description="Zero-LLM data quality & compliance gateway for RAG systems.",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # ---- filter ------------------------------------------------------------
    flt = sub.add_parser(
        "filter",
        help="Filter text chunks through the full quality pipeline.",
        description=(
            "Read chunks from INPUT (.jsonl or .txt), run them through all active "
            "quality gates, and write accepted chunks to OUTPUT (stdout by default). "
            "Rejected chunks are silently dropped unless --rejected is given."
        ),
    )
    flt.add_argument(
        "input",
        metavar="INPUT",
        help="Input file (.jsonl or .txt). Use '-' for stdin.",
    )
    flt.add_argument(
        "output",
        metavar="OUTPUT",
        nargs="?",
        default="-",
        help="Output file. Use '-' for stdout (default).",
    )

    # Config file
    flt.add_argument(
        "--config",
        metavar="FILE",
        help="Path to a .yaml/.yml or .toml config file. CLI flags override file values.",
    )

    # Format
    flt.add_argument(
        "--format",
        choices=["jsonl", "txt", "auto"],
        default="auto",
        metavar="FMT",
        help="Input format: jsonl | txt | auto (default: auto-detect from extension).",
    )
    flt.add_argument(
        "--text-field",
        default="text",
        metavar="FIELD",
        help="JSON key containing the chunk text (default: text).",
    )

    # Length
    flt.add_argument("--min-length", type=int, default=None, metavar="N",
                     help="Minimum chunk length in characters.")
    flt.add_argument("--max-length", type=int, default=None, metavar="N",
                     help="Maximum chunk length in characters.")

    # Gate toggles
    flt.add_argument("--no-pii", action="store_true",
                     help="Disable PII masking.")
    flt.add_argument("--no-dedup", action="store_true",
                     help="Disable all deduplication (exact + fuzzy).")
    flt.add_argument("--no-fuzzy", action="store_true",
                     help="Disable fuzzy (MinHash) deduplication only.")
    flt.add_argument("--no-entropy", action="store_true",
                     help="Disable entropy / gibberish filter.")

    # European PII opt-ins
    flt.add_argument("--pii-iban", action="store_true",
                     help="Enable IBAN detection (European bank accounts, mod-97 validated).")
    flt.add_argument("--pii-eu-vat", action="store_true",
                     help="Enable EU VAT number detection (all 27 member states + UK).")
    flt.add_argument("--pii-eu-phone", action="store_true",
                     help="Enable European local phone number detection (UK/FR/DE formats).")

    # Output / audit
    flt.add_argument(
        "--rejected",
        metavar="FILE",
        help="Write rejected chunks to this .jsonl file (includes rejection reason).",
    )
    flt.add_argument("--no-dlq", action="store_true",
                     help="Disable the SQLite dead-letter queue.")
    flt.add_argument("--stats", action="store_true",
                     help="Print summary statistics to stderr after processing.")

    # ---- mask --------------------------------------------------------------
    msk = sub.add_parser(
        "mask",
        help="Apply PII masking only (no other quality gates).",
        description=(
            "Read chunks from INPUT and write PII-masked text to OUTPUT. "
            "No deduplication, entropy, or length filtering is applied."
        ),
    )
    msk.add_argument("input", metavar="INPUT",
                     help="Input file (.jsonl or .txt). Use '-' for stdin.")
    msk.add_argument("output", metavar="OUTPUT", nargs="?", default="-",
                     help="Output file. Use '-' for stdout (default).")
    msk.add_argument("--format", choices=["jsonl", "txt", "auto"], default="auto",
                     metavar="FMT", help="Input format (default: auto).")
    msk.add_argument("--text-field", default="text", metavar="FIELD",
                     help="JSON key containing the chunk text (default: text).")
    msk.add_argument("--pii-iban", action="store_true",
                     help="Enable IBAN detection.")
    msk.add_argument("--pii-eu-vat", action="store_true",
                     help="Enable EU VAT detection.")
    msk.add_argument("--pii-eu-phone", action="store_true",
                     help="Enable EU local phone detection.")
    msk.add_argument("--stats", action="store_true",
                     help="Print PII hit count to stderr.")

    # ---- serve -------------------------------------------------------------
    srv = sub.add_parser(
        "serve",
        help="Start the REST API server (requires taparash[api]).",
        description=(
            "Start a FastAPI server that exposes /filter, /filter/single, "
            "/mask, /health, and /stats endpoints."
        ),
    )
    srv.add_argument("--host", default="127.0.0.1",
                     help="Bind host (default: 127.0.0.1).")
    srv.add_argument("--port", type=int, default=8000,
                     help="Bind port (default: 8000).")
    srv.add_argument("--config", metavar="FILE",
                     help="Config file (.yaml or .toml).")
    srv.add_argument("--workers", type=int, default=1,
                     help="Number of uvicorn worker processes (default: 1).")
    srv.add_argument("--reload", action="store_true",
                     help="Enable auto-reload (development mode).")

    # ---- version -----------------------------------------------------------
    sub.add_parser("version", help="Print taparash version and exit.")

    return parser


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def _detect_format(path: str) -> str:
    if path == "-":
        return "jsonl"
    lower = path.lower()
    if lower.endswith(".jsonl") or lower.endswith(".ndjson"):
        return "jsonl"
    if lower.endswith(".txt") or lower.endswith(".text"):
        return "txt"
    return "jsonl"  # safest default


def _iter_chunks(
    path: str, fmt: str, text_field: str
) -> Iterator[Tuple[str, dict]]:
    """Yield (text, record) pairs from the input file."""
    fh: IO = sys.stdin if path == "-" else open(path, encoding="utf-8")
    try:
        for lineno, raw in enumerate(fh, 1):
            line = raw.rstrip("\n")
            if not line:
                continue
            if fmt == "jsonl":
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    print(
                        f"[taparash] warning: skipping malformed JSON on line {lineno}",
                        file=sys.stderr,
                    )
                    continue
                yield obj.get(text_field, ""), obj
            else:
                yield line, {text_field: line}
    finally:
        if path != "-":
            fh.close()


def _write_record(fh: IO, text: str, record: dict, text_field: str, fmt: str) -> None:
    if fmt == "jsonl":
        out = dict(record)
        out[text_field] = text
        fh.write(json.dumps(out, ensure_ascii=False) + "\n")
    else:
        fh.write(text + "\n")


def _open_output(path: str) -> Tuple[IO, bool]:
    """Return (file_handle, should_close)."""
    if path == "-":
        return sys.stdout, False
    return open(path, "w", encoding="utf-8"), True


# ---------------------------------------------------------------------------
# Command implementations
# ---------------------------------------------------------------------------

def _cmd_filter(args) -> int:
    try:
        from taparash.config import QualityConfig
        from taparash.config_io import load_config
        from taparash.pipeline import TaparashFilter
    except ImportError:
        print(
            "Error: taparash package not installed. Run: pip install taparash",
            file=sys.stderr,
        )
        return 1

    # Start from config file if given, then apply CLI overrides
    if getattr(args, "config", None):
        try:
            base = load_config(args.config)
        except (ValueError, ImportError, FileNotFoundError) as exc:
            print(f"Config file error: {exc}", file=sys.stderr)
            return 1
        import dataclasses
        kwargs: dict = {
            f.name: getattr(base, f.name)
            for f in dataclasses.fields(base)
            if getattr(base, f.name) is not None and not callable(getattr(base, f.name))
        }
    else:
        kwargs = {}

    if args.min_length is not None:
        kwargs["min_chunk_length"] = args.min_length
    if args.max_length is not None:
        kwargs["max_chunk_length"] = args.max_length
    if args.no_pii:
        kwargs["enable_pii_masking"] = False
    if args.no_dedup:
        kwargs["enable_exact_dedup"] = False
        kwargs["enable_fuzzy_dedup"] = False
    elif args.no_fuzzy:
        kwargs["enable_fuzzy_dedup"] = False
    if args.no_entropy:
        kwargs["enable_entropy_check"] = False
    if args.pii_iban:
        kwargs["pii_mask_iban"] = True
    if args.pii_eu_vat:
        kwargs["pii_mask_eu_vat"] = True
    if args.pii_eu_phone:
        kwargs["pii_mask_eu_phone"] = True
    if args.no_dlq:
        kwargs["enable_dlq"] = False

    try:
        config = QualityConfig(**kwargs)
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    pipeline = TaparashFilter(config)
    fmt = args.format if args.format != "auto" else _detect_format(args.input)
    out_fh, close_out = _open_output(args.output)
    rej_fh = open(args.rejected, "w", encoding="utf-8") if args.rejected else None

    accepted = rejected = 0
    try:
        for text, record in _iter_chunks(args.input, fmt, args.text_field):
            result = pipeline.process_single(text)
            if result.is_valid:
                _write_record(out_fh, result.text, record, args.text_field, fmt)
                accepted += 1
            else:
                if rej_fh:
                    rej_record = dict(record)
                    rej_record["_taparash_reason"] = result.reason_code
                    rej_fh.write(json.dumps(rej_record, ensure_ascii=False) + "\n")
                rejected += 1
    finally:
        if close_out:
            out_fh.close()
        if rej_fh:
            rej_fh.close()

    if args.stats:
        total = accepted + rejected
        rate = f"{accepted / total * 100:.1f}%" if total else "n/a"
        print(
            f"Processed: {total}  Accepted: {accepted}  Rejected: {rejected}  ({rate})",
            file=sys.stderr,
        )

    return 0


def _cmd_serve(args) -> int:
    try:
        import uvicorn
        from taparash.server import create_app
    except ImportError as exc:
        print(
            f"Error: {exc}\nInstall the API extra: pip install taparash[api]",
            file=sys.stderr,
        )
        return 1

    config = None
    if getattr(args, "config", None):
        try:
            from taparash.config_io import load_config
            config = load_config(args.config)
        except (ValueError, ImportError, FileNotFoundError) as exc:
            print(f"Config file error: {exc}", file=sys.stderr)
            return 1

    app = create_app(config)
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        workers=args.workers if not args.reload else 1,
        reload=args.reload,
    )
    return 0


def _cmd_mask(args) -> int:
    try:
        from taparash.core.pii import PIIMasker
    except ImportError:
        print("Error: taparash package not installed.", file=sys.stderr)
        return 1

    masker = PIIMasker(
        mask_iban=args.pii_iban,
        mask_eu_vat=args.pii_eu_vat,
        mask_eu_phone=args.pii_eu_phone,
    )
    fmt = args.format if args.format != "auto" else _detect_format(args.input)
    out_fh, close_out = _open_output(args.output)
    total_hits = 0

    try:
        for text, record in _iter_chunks(args.input, fmt, args.text_field):
            masked, matches = masker.mask(text)
            total_hits += len(matches)
            _write_record(out_fh, masked, record, args.text_field, fmt)
    finally:
        if close_out:
            out_fh.close()

    if args.stats:
        print(f"PII hits: {total_hits}", file=sys.stderr)

    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "version":
        try:
            from taparash import __version__
            print(f"taparash {__version__}")
        except ImportError:
            print("taparash (version unknown)")
        return

    if args.command == "filter":
        sys.exit(_cmd_filter(args))

    if args.command == "mask":
        sys.exit(_cmd_mask(args))

    if args.command == "serve":
        sys.exit(_cmd_serve(args))


if __name__ == "__main__":
    main()
