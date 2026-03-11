#!/usr/bin/env python3
"""
Sample.py — Windows inference smoke test for BitNet b1.58 2B on Windows 11.

Runs a single BitNet inference via llama-cli.exe, prints the output, and
reports token-generation speed.  Use this as a quick sanity check after
building BitNet with setup_env.py.

Usage (from inside the BitNet clone directory):
    python Sample.py               # from inside the BitNet/ directory
    python Sample.py               # if Sample.py is copied into BitNet/

Prerequisites:
    - BitNet built:   python setup_env.py -md models\\BitNet-b1.58-2B-4T -q i2_s
    - Model present:  models\\BitNet-b1.58-2B-4T\\ggml-model-i2_s.gguf
"""

import os
import re
import subprocess
import sys
import time
from pathlib import Path


# ---------------------------------------------------------------------------
# Configuration — auto-detect paths
# ---------------------------------------------------------------------------

def _find(candidates: list[Path]) -> Path:
    """Return the first existing path from *candidates*, or the last entry."""
    for p in candidates:
        if p.exists():
            return p
    return candidates[-1]


LLAMA_CLI = _find([
    Path("build") / "bin" / "Release" / "llama-cli.exe",
    Path("build") / "bin" / "llama-cli.exe",
    Path("build") / "bin" / "Debug" / "llama-cli.exe",
])

MODEL_PATH = _find([
    Path("models") / "BitNet-b1.58-2B-4T" / "ggml-model-i2_s.gguf",
])

PROMPT = (
    "Explain in one paragraph what makes 1-bit large language models "
    "efficient compared to traditional floating-point models."
)

NUM_TOKENS  = 80
NUM_THREADS = os.cpu_count() or 8


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_speed(stderr_output: str) -> str:
    """Extract tokens-per-second from llama-cli's performance summary."""
    # Example: "llama_perf_sampler_print:    ... eval time = 1234.56 ms / 80 tokens ( 15.43 ms per token, 64.81 tokens per second)"
    match = re.search(r"([\d.]+)\s+tokens per second", stderr_output)
    if match:
        return f"{float(match.group(1)):.1f} tok/s"
    # Fallback: eval time
    match = re.search(r"eval time\s*=\s*([\d.]+)\s*ms\s*/\s*(\d+)\s*tokens", stderr_output)
    if match:
        ms, toks = float(match.group(1)), int(match.group(2))
        if ms > 0:
            return f"{toks / ms * 1000:.1f} tok/s"
    return "(speed not available)"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Run a single inference and print timing information."""
    print("=" * 60)
    print("  BitNet Sample Inference — Windows 11 / Intel Panther Lake")
    print("=" * 60)
    print(f"  Executable : {LLAMA_CLI}")
    print(f"  Model      : {MODEL_PATH}")
    print(f"  Threads    : {NUM_THREADS}")
    print(f"  Prompt     : {PROMPT[:60]}...")
    print()

    # --- Pre-flight checks ---
    if not LLAMA_CLI.exists():
        print(f"[ERROR] llama-cli.exe not found at '{LLAMA_CLI}'.")
        print("        Build BitNet first:")
        print("          python setup_env.py -md models\\BitNet-b1.58-2B-4T -q i2_s")
        sys.exit(1)

    if not MODEL_PATH.exists():
        print(f"[ERROR] Model not found at '{MODEL_PATH}'.")
        print("        Download it:")
        print("          huggingface-cli download microsoft/BitNet-b1.58-2B-4T-gguf "
              "--local-dir models\\BitNet-b1.58-2B-4T")
        sys.exit(1)

    # --- Run inference ---
    cmd = [
        str(LLAMA_CLI),
        "-m", str(MODEL_PATH),
        "-p", PROMPT,
        "-n", str(NUM_TOKENS),
        "-t", str(NUM_THREADS),
        "--no-warmup",
        "-e",
    ]

    print("Running inference...\n")
    wall_start = time.perf_counter()

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=180)
    except FileNotFoundError:
        print(f"[ERROR] Could not launch '{LLAMA_CLI}'.")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("[ERROR] Inference timed out after 180 seconds.")
        sys.exit(1)

    wall_elapsed = time.perf_counter() - wall_start

    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")

    if result.returncode != 0:
        print(f"[ERROR] llama-cli.exe exited with code {result.returncode}.")
        print(stderr[-2000:])  # last 2000 characters of stderr for diagnostics
        sys.exit(result.returncode)

    # --- Print system_info line (shows AVX/AMX flags) ---
    for line in stderr.splitlines():
        if line.startswith("system_info:"):
            print(f"[system_info] {line}")
            break

    # --- Print model output ---
    print("\n--- Model output ---")
    print(stdout.strip())
    print("--- End ---\n")

    # --- Print timing summary ---
    speed = parse_speed(stderr)
    print(f"  Wall time : {wall_elapsed:.1f}s")
    print(f"  Speed     : {speed}")
    print()
    print("Smoke test PASSED ✓")


if __name__ == "__main__":
    main()
