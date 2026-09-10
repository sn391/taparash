#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Taparash throughput benchmark harness.

Produces hardware-normalised MB/s-per-core numbers and per-gate latency
breakdown in both JSON and Markdown formats, ready for conference appendices
or README tables.

Usage
-----
    python benchmarks/run_benchmark.py              # full suite (~3 min)
    python benchmarks/run_benchmark.py --quick      # fast smoke-test (~25 s)
    python benchmarks/run_benchmark.py --output-dir results/

Requirements
------------
    pip install taparash          # core package
    pip install psutil            # optional — improves memory measurement

Methodology
-----------
Chunks are sampled from a realistic length distribution (µ=350 chars,
σ=180, clipped to [50,1500]) seeded for reproducibility.  10 % of chunks
contain synthetic PII, 5 % are near-duplicates, 3 % are high-entropy noise.
Each metric reports median, P95, and P99 over MEASURE iterations after a
WARMUP phase.  Throughput is computed from raw UTF-8 byte size of inputs.
MB/s/core divides by logical CPU count at benchmark time.

Comparison guidance
-------------------
When comparing with other tools (NeMo Curator, Unstructured.io, etc.):
  1. Run this script on your hardware to get taparash numbers.
  2. Run the competing tool's own benchmark on the *same* machine.
  3. Report CPU model, core count, RAM, and OS for all three.
  4. Note what each tool actually does — scope differs significantly.
"""

import argparse
import io
import json
import math
import multiprocessing
import os
import platform
import random
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Optional psutil for better memory measurement
# ---------------------------------------------------------------------------
try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False


# ---------------------------------------------------------------------------
# Synthetic data generation
# ---------------------------------------------------------------------------

_WORDS = (
    "the quick brown fox jumps over lazy dog machine learning artificial "
    "intelligence data quality pipeline text processing compliance privacy "
    "enterprise security filter deduplication entropy validation masking "
    "batch processing throughput latency benchmark performance scalability "
    "regex pattern detection classification annotation retrieval augmented "
    "generation embedding vector database chunk document paragraph section "
    "accuracy precision recall threshold configuration parameter worker"
).split()

_PII_TEMPLATES = [
    "Contact {name} at {email} or call {phone}.",
    "Please send invoice to {email} before end of quarter.",
    "Card number {cc} expires next month.",
    "SSN on file: {ssn}.",
    "Reach out to {name} via {email} for details.",
]

_NAMES = ["Alice Johnson", "Bob Smith", "Carol White", "David Lee", "Eva Brown"]
_EMAILS = ["alice@example.com", "bob@corp.org", "carol@test.net", "dave@company.io"]
_PHONES = ["555-123-4567", "(800) 555-0199", "+1-415-555-0123"]
_CCS = ["4532-1488-0343-6467", "5425-2334-3010-9903"]
_SSNS = ["123-45-6789", "987-65-4321"]


def _random_word_chunk(rng: random.Random, length: int) -> str:
    words = []
    cur = 0
    while cur < length:
        w = rng.choice(_WORDS)
        words.append(w)
        cur += len(w) + 1
    return " ".join(words)


def _pii_chunk(rng: random.Random) -> str:
    tmpl = rng.choice(_PII_TEMPLATES)
    return tmpl.format(
        name=rng.choice(_NAMES),
        email=rng.choice(_EMAILS),
        phone=rng.choice(_PHONES),
        cc=rng.choice(_CCS),
        ssn=rng.choice(_SSNS),
    )


def _high_entropy_chunk(rng: random.Random, length: int = 80) -> str:
    chars = "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()_+-=[]{}|;:,.<>?"
    return "".join(rng.choice(chars) for _ in range(length))


def generate_chunks(
    n: int,
    seed: int = 42,
    pii_frac: float = 0.10,
    noise_frac: float = 0.03,
    dup_frac: float = 0.05,
) -> List[str]:
    """
    Generate n synthetic text chunks with realistic length distribution.

    Distribution: µ=350 chars, σ=180, clipped to [50, 1500].
    pii_frac  : fraction containing synthetic PII patterns
    noise_frac: fraction of high-entropy (gibberish) chunks
    dup_frac  : fraction that are near-duplicates of earlier chunks
    """
    rng = random.Random(seed)
    base: List[str] = []

    for _ in range(n):
        r = rng.random()
        if r < noise_frac:
            base.append(_high_entropy_chunk(rng))
        elif r < noise_frac + pii_frac:
            base.append(_pii_chunk(rng))
        else:
            length = max(50, min(1500, int(rng.gauss(350, 180))))
            base.append(_random_word_chunk(rng, length))

    # Inject near-duplicates
    n_dups = int(n * dup_frac)
    sources = base[:max(1, len(base) - n_dups)]
    for i in range(n_dups):
        src = rng.choice(sources)
        words = src.split()
        if len(words) > 3:
            idx = rng.randint(0, len(words) - 1)
            words[idx] = rng.choice(_WORDS)
        base.append(" ".join(words))

    rng.shuffle(base)
    return base[:n]


# ---------------------------------------------------------------------------
# Hardware information
# ---------------------------------------------------------------------------

def get_hardware_info() -> Dict[str, Any]:
    cpu_count_logical = multiprocessing.cpu_count()
    try:
        cpu_count_physical = len(set(
            line.split(":")[1].strip()
            for line in open("/proc/cpuinfo")
            if "physical id" in line
        )) if os.path.exists("/proc/cpuinfo") else cpu_count_logical // 2
    except Exception:
        cpu_count_physical = cpu_count_logical // 2 or 1

    ram_gb: Optional[float] = None
    if _PSUTIL:
        ram_gb = round(psutil.virtual_memory().total / 1e9, 1)
    elif platform.system() == "Windows":
        try:
            import ctypes
            class _MEMSTATUS(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            ms = _MEMSTATUS()
            ms.dwLength = ctypes.sizeof(_MEMSTATUS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))  # type: ignore[attr-defined]
            ram_gb = round(ms.ullTotalPhys / 1e9, 1)
        except Exception:
            pass
    else:
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal"):
                        ram_gb = round(int(line.split()[1]) / 1e6, 1)
                        break
        except Exception:
            pass

    cpu_model = platform.processor() or platform.machine()

    return {
        "cpu_model": cpu_model,
        "cpu_logical_cores": cpu_count_logical,
        "cpu_physical_cores": cpu_count_physical,
        "ram_gb": ram_gb,
        "os": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "date_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }


# ---------------------------------------------------------------------------
# Memory measurement
# ---------------------------------------------------------------------------

def _peak_rss_mb() -> float:
    if _PSUTIL:
        return psutil.Process(os.getpid()).memory_info().rss / 1e6
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Benchmark helpers
# ---------------------------------------------------------------------------

def _total_bytes(chunks: List[str]) -> int:
    return sum(len(c.encode("utf-8")) for c in chunks)


def _run_batch(f, chunks: List[str]) -> float:
    """Return wall-clock seconds for one process_batch call."""
    t0 = time.perf_counter()
    f.process_batch(chunks)
    return time.perf_counter() - t0


def _percentile(data: List[float], p: float) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = (len(sorted_data) - 1) * p / 100
    lo = int(idx)
    hi = lo + 1
    if hi >= len(sorted_data):
        return sorted_data[-1]
    return sorted_data[lo] + (idx - lo) * (sorted_data[hi] - sorted_data[lo])


def _bench_config(
    config_kwargs: Dict[str, Any],
    chunks: List[str],
    warmup: int,
    measure: int,
    use_parallel: bool = False,
) -> Dict[str, float]:
    """Run warmup+measure iterations; return stats dict."""
    from taparash import TaparashFilter, QualityConfig

    times: List[float] = []
    for i in range(warmup + measure):
        f = TaparashFilter(QualityConfig(**config_kwargs))
        elapsed = _run_batch(f, chunks)
        if i >= warmup:
            times.append(elapsed)

    n_chunks = len(chunks)
    n_bytes = _total_bytes(chunks)
    throughputs_cps = [n_chunks / t for t in times]
    throughputs_mbs = [n_bytes / t / 1e6 for t in times]

    return {
        "median_sec": statistics.median(times),
        "p95_sec": _percentile(times, 95),
        "p99_sec": _percentile(times, 99),
        "median_chunks_per_sec": statistics.median(throughputs_cps),
        "median_mb_per_sec": statistics.median(throughputs_mbs),
        "p95_mb_per_sec": _percentile(throughputs_mbs, 5),  # 5th pct = worst case
    }


# ---------------------------------------------------------------------------
# Gate isolation configs
# ---------------------------------------------------------------------------

_BASE_DISABLED = dict(
    enable_pii_masking=False,
    enable_entropy_check=False,
    enable_exact_dedup=False,
    enable_fuzzy_dedup=False,
    enable_semantic_dedup=False,
    check_contradictions=False,
    enable_dlq=False,
    min_chunk_length=1,
    max_chunk_length=999_999,
)

GATE_CONFIGS = {
    "length_validation": {
        **_BASE_DISABLED,
        "min_chunk_length": 20,
        "max_chunk_length": 2000,
    },
    "pii_masking": {
        **_BASE_DISABLED,
        "enable_pii_masking": True,
    },
    "entropy_check": {
        **_BASE_DISABLED,
        "enable_entropy_check": True,
        "entropy_threshold": 4.2,
    },
    "exact_dedup": {
        **_BASE_DISABLED,
        "enable_exact_dedup": True,
    },
    "fuzzy_dedup": {
        **_BASE_DISABLED,
        "enable_fuzzy_dedup": True,
        "fuzzy_num_perm": 128,
    },
    "full_pipeline": dict(
        min_chunk_length=20,
        max_chunk_length=2000,
        enable_pii_masking=True,
        enable_entropy_check=True,
        enable_exact_dedup=True,
        enable_fuzzy_dedup=True,
        enable_semantic_dedup=False,
        check_contradictions=False,
        enable_dlq=False,
    ),
}


# ---------------------------------------------------------------------------
# Main benchmark suites
# ---------------------------------------------------------------------------

def bench_per_gate(
    chunks: List[str], warmup: int, measure: int
) -> Dict[str, Dict[str, float]]:
    """Isolate each gate and measure median µs/chunk, P95, P99."""
    results = {}
    for gate_name, cfg in GATE_CONFIGS.items():
        print(f"  [{gate_name}] ...", end=" ", flush=True)
        stats = _bench_config(cfg, chunks, warmup, measure)
        n = len(chunks)
        results[gate_name] = {
            "median_us_per_chunk": stats["median_sec"] / n * 1e6,
            "p95_us_per_chunk": stats["p95_sec"] / n * 1e6,
            "p99_us_per_chunk": stats["p99_sec"] / n * 1e6,
            "median_chunks_per_sec": stats["median_chunks_per_sec"],
            "median_mb_per_sec": stats["median_mb_per_sec"],
        }
        print(f"{results[gate_name]['median_us_per_chunk']:.1f} us/chunk")
    return results


def bench_throughput(
    all_chunks: List[str],
    batch_sizes: List[int],
    cpu_cores: int,
    warmup: int,
    measure: int,
) -> List[Dict[str, Any]]:
    """Measure end-to-end throughput at different batch sizes."""
    cfg = GATE_CONFIGS["full_pipeline"]
    rows = []
    for bs in batch_sizes:
        chunks = all_chunks[:bs]
        print(f"  [batch={bs}] ...", end=" ", flush=True)
        stats = _bench_config(cfg, chunks, warmup, measure)
        rows.append({
            "batch_size": bs,
            "chunks_per_sec": round(stats["median_chunks_per_sec"]),
            "mb_per_sec": round(stats["median_mb_per_sec"], 2),
            "mb_per_sec_per_core": round(stats["median_mb_per_sec"] / cpu_cores, 3),
            "median_sec": round(stats["median_sec"], 4),
        })
        print(
            f"{rows[-1]['chunks_per_sec']:,} chunks/s  "
            f"{rows[-1]['mb_per_sec']} MB/s  "
            f"{rows[-1]['mb_per_sec_per_core']} MB/s/core"
        )
    return rows


def bench_scaling(
    chunks: List[str],
    worker_counts: List[int],
    warmup: int,
    measure: int,
) -> List[Dict[str, Any]]:
    """Measure throughput vs parallel worker count."""
    base_cfg = GATE_CONFIGS["full_pipeline"]
    rows = []
    for nw in worker_counts:
        cfg = {**base_cfg, "parallel_workers": nw}
        print(f"  [workers={nw}] ...", end=" ", flush=True)
        from taparash import TaparashFilter, QualityConfig
        times: List[float] = []
        for i in range(warmup + measure):
            f = TaparashFilter(QualityConfig(**cfg))
            t0 = time.perf_counter()
            f.process_batch(chunks, use_parallel=(nw > 1))
            elapsed = time.perf_counter() - t0
            if i >= warmup:
                times.append(elapsed)
        n_bytes = _total_bytes(chunks)
        mbs = statistics.median([n_bytes / t / 1e6 for t in times])
        cps = statistics.median([len(chunks) / t for t in times])
        rows.append({
            "workers": nw,
            "chunks_per_sec": round(cps),
            "mb_per_sec": round(mbs, 2),
        })
        print(f"{rows[-1]['chunks_per_sec']:,} chunks/s  {rows[-1]['mb_per_sec']} MB/s")
    return rows


def bench_memory(chunks: List[str]) -> Dict[str, float]:
    """Measure peak RSS before and after processing 100k tokens."""
    from taparash import TaparashFilter, QualityConfig
    f = TaparashFilter(QualityConfig(**GATE_CONFIGS["full_pipeline"]))
    before = _peak_rss_mb()
    f.process_batch(chunks)
    after = _peak_rss_mb()
    total_tokens = sum(len(c.split()) for c in chunks)
    delta = max(0.0, after - before)
    return {
        "rss_before_mb": round(before, 1),
        "rss_after_mb": round(after, 1),
        "delta_mb": round(delta, 1),
        "mb_per_million_tokens": round(delta / total_tokens * 1e6, 1) if total_tokens else 0.0,
    }


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def format_markdown(results: Dict[str, Any]) -> str:
    hw = results["hardware"]
    lines = [
        "## Taparash Benchmark Results",
        "",
        f"**CPU:** {hw['cpu_model']}  ",
        f"**Cores:** {hw['cpu_logical_cores']} logical / {hw['cpu_physical_cores']} physical  ",
        f"**RAM:** {hw.get('ram_gb', 'N/A')} GB  ",
        f"**OS:** {hw['os']}  ",
        f"**Python:** {hw['python']}  ",
        f"**Date:** {hw['date_utc']}  ",
        "",
        "> Numbers below are from a single run on the hardware above.",
        "> Re-run `python benchmarks/run_benchmark.py` to get numbers for your machine.",
        "",
        "### End-to-End Throughput (full pipeline)",
        "",
        "| Batch size | Chunks/s | MB/s | MB/s per core |",
        "|-----------|---------|------|---------------|",
    ]
    for row in results["throughput"]:
        lines.append(
            f"| {row['batch_size']:,} "
            f"| {row['chunks_per_sec']:,} "
            f"| {row['mb_per_sec']} "
            f"| {row['mb_per_sec_per_core']} |"
        )

    lines += [
        "",
        "### Per-Gate Latency (median µs / chunk, 1k-chunk batch)",
        "",
        "| Gate | Median µs | P95 µs | P99 µs |",
        "|------|-----------|--------|--------|",
    ]
    for gate, s in results["per_gate"].items():
        lines.append(
            f"| {gate.replace('_', ' ').title()} "
            f"| {s['median_us_per_chunk']:.1f} "
            f"| {s['p95_us_per_chunk']:.1f} "
            f"| {s['p99_us_per_chunk']:.1f} |"
        )

    lines += [
        "",
        "### Parallel Scaling (full pipeline, 1000 chunks)",
        "",
        "| Workers | Chunks/s | MB/s |",
        "|---------|---------|------|",
    ]
    for row in results["scaling"]:
        lines.append(f"| {row['workers']} | {row['chunks_per_sec']:,} | {row['mb_per_sec']} |")

    mem = results["memory"]
    lines += [
        "",
        "### Memory",
        "",
        f"- RSS delta for 10k-chunk batch: **{mem['delta_mb']} MB**",
        f"- Normalised: **{mem['mb_per_million_tokens']} MB per million tokens**",
        "",
        "---",
        "",
        "### Comparison Guidance",
        "",
        "To compare with other tools on the same hardware:",
        "",
        "| Tool | What it measures | How to run |",
        "|------|-----------------|-----------|",
        "| **taparash** | Quality filtering throughput | `python benchmarks/run_benchmark.py` |",
        "| **NeMo Curator** | Dataset curation (GPU-accelerated) | `python nemo_curator_benchmark.py` ¹ |",
        "| **Unstructured.io** | Document parsing throughput | `python unstructured_benchmark.py` ¹ |",
        "",
        "¹ Script not included — run the respective tool's own benchmark on the same machine",
        "  and record its MB/s/core using identical input files.",
        "",
        "> Note: these tools solve different sub-problems.",
        "> Taparash focuses on *post-parse* quality filtering (dedup, PII, entropy).",
        "> NeMo Curator includes parsing, fuzzy dedup, and quality scoring.",
        "> Unstructured.io focuses on *parsing* unstructured documents.",
        "> A fair comparison should report each tool's scope alongside the numbers.",
    ]
    return "\n".join(lines)


def save_results(results: Dict[str, Any], output_dir: Path) -> Tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    hw = results["hardware"]
    stamp = f"{hw['date_utc']}_{platform.node().replace('.', '-')}"

    json_path = output_dir / f"benchmark_{stamp}.json"
    md_path = output_dir / f"benchmark_{stamp}.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(format_markdown(results))

    return json_path, md_path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Taparash benchmark harness")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Reduced suite for CI / smoke testing (faster, less data)",
    )
    parser.add_argument(
        "--output-dir",
        default="benchmarks/results",
        help="Directory to write JSON and Markdown results (default: benchmarks/results)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for synthetic data generation (default: 42)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    if args.quick:
        WARMUP, MEASURE = 1, 2
        BATCH_SIZES = [100, 500]
        GATE_CHUNKS = 500
        THROUGHPUT_CHUNKS = 500
        SCALING_CHUNKS = 300
        MEMORY_CHUNKS = 2_000
        WORKER_COUNTS = [1, 2]
    else:
        WARMUP, MEASURE = 2, 5
        BATCH_SIZES = [100, 1_000, 5_000, 10_000]
        GATE_CHUNKS = 1_000
        THROUGHPUT_CHUNKS = 10_000
        SCALING_CHUNKS = 1_000
        MEMORY_CHUNKS = 10_000
        WORKER_COUNTS = [1, 2, 4, max(1, multiprocessing.cpu_count() // 2)]
        WORKER_COUNTS = sorted(set(WORKER_COUNTS))

    hw = get_hardware_info()
    print("=" * 65)
    print("  Taparash Benchmark Harness")
    print("=" * 65)
    print(f"  CPU    : {hw['cpu_model']}")
    print(f"  Cores  : {hw['cpu_logical_cores']} logical")
    print(f"  RAM    : {hw.get('ram_gb', 'N/A')} GB")
    print(f"  OS     : {hw['os']}")
    print(f"  Python : {hw['python']}")
    print(f"  Mode   : {'quick' if args.quick else 'full'}")
    print("=" * 65)

    # Generate data once
    max_n = max(BATCH_SIZES + [GATE_CHUNKS, THROUGHPUT_CHUNKS, SCALING_CHUNKS, MEMORY_CHUNKS])
    print(f"\nGenerating {max_n:,} synthetic chunks ... ", end="", flush=True)
    all_chunks = generate_chunks(max_n, seed=args.seed)
    total_mb = _total_bytes(all_chunks) / 1e6
    print(f"done  ({total_mb:.1f} MB, avg {int(total_mb*1e6/max_n)} bytes/chunk)")

    # --- Per-gate latency ---
    print(f"\n[1/4] Per-gate latency  ({GATE_CHUNKS} chunks, {WARMUP}W+{MEASURE}M iters)")
    per_gate = bench_per_gate(all_chunks[:GATE_CHUNKS], WARMUP, MEASURE)

    # --- Throughput ---
    print(f"\n[2/4] End-to-end throughput  ({WARMUP}W+{MEASURE}M iters per batch size)")
    throughput = bench_throughput(
        all_chunks[:THROUGHPUT_CHUNKS],
        [bs for bs in BATCH_SIZES if bs <= THROUGHPUT_CHUNKS],
        hw["cpu_logical_cores"],
        WARMUP,
        MEASURE,
    )

    # --- Parallel scaling ---
    print(f"\n[3/4] Parallel scaling  ({SCALING_CHUNKS} chunks, workers={WORKER_COUNTS})")
    scaling = bench_scaling(all_chunks[:SCALING_CHUNKS], WORKER_COUNTS, WARMUP, MEASURE)

    # --- Memory ---
    print(f"\n[4/4] Memory  ({MEMORY_CHUNKS} chunks)")
    memory = bench_memory(all_chunks[:MEMORY_CHUNKS])
    print(
        f"  RSS delta: {memory['delta_mb']} MB  "
        f"({memory['mb_per_million_tokens']} MB/M tokens)"
    )

    results = {
        "hardware": hw,
        "per_gate": per_gate,
        "throughput": throughput,
        "scaling": scaling,
        "memory": memory,
        "config": {
            "warmup_iters": WARMUP,
            "measure_iters": MEASURE,
            "seed": args.seed,
            "quick_mode": args.quick,
        },
    }

    json_path, md_path = save_results(results, output_dir)

    print(f"\n{'=' * 65}")
    print("  Results saved to:")
    print(f"    JSON : {json_path}")
    print(f"    MD   : {md_path}")
    print("=" * 65)
    print()
    print(format_markdown(results))


if __name__ == "__main__":
    # Ensure UTF-8 output on Windows so µ/σ in the Markdown table survive
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
