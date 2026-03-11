#!/usr/bin/env python3
"""
Multi-turn chat script for BitNet on Windows 11.
Equivalent of the macOS chat.py from the Apple Silicon demo,
adapted for Windows paths and x86-64 (Panther Lake) CPUs.
"""

import subprocess
import sys
import re
import os

# ── paths ────────────────────────────────────────────────────────────────────
MODEL_PATH  = r"models\BitNet-b1.58-2B-4T\ggml-model-i2_s.gguf"
LLAMA_CLI   = r"build\bin\Release\llama-cli.exe"

# ── token budget ─────────────────────────────────────────────────────────────
MAX_NEW_TOKENS   = 200
RESPONSE_CUTOFF  = 1000   # chars

# ── thread count hint ─────────────────────────────────────────────────────────
def _physical_cores():
    """Return physical core count (not logical); fall back to cpu_count."""
    try:
        import psutil
        return psutil.cpu_count(logical=False) or os.cpu_count() or 8
    except ImportError:
        return os.cpu_count() or 8

NUM_THREADS = _physical_cores()


def extract_response(output: str) -> str:
    """Strip llama.cpp metadata and return only the assistant text."""
    skip_prefixes = (
        "llama_", "ggml_", "llm_load", "main:", "build:",
        "sampler", "generate:", "common_", "check_double",
        "\t", "system_info",
    )
    lines = output.split("\n")
    filtered, in_output = [], False

    for line in lines:
        if any(line.strip().startswith(p) for p in skip_prefixes):
            continue
        if not in_output and not line.strip():
            continue
        if "llama_perf" in line or "tokens per second" in line:
            break
        in_output = True
        filtered.append(line)

    text = "\n".join(filtered).strip()

    if "BITNETAssistant:" in text:
        text = text.split("BITNETAssistant:")[-1].strip()

    text = text.replace("[end of text]", "").strip()
    text = re.sub(r"\s*Human:\s*$", "", text)
    return text


def chat():
    # ── verify paths ──────────────────────────────────────────────────────────
    if not os.path.isfile(LLAMA_CLI):
        print(f"[ERROR] llama-cli not found at: {LLAMA_CLI}")
        print("        Build BitNet first (see windows/README.md).")
        sys.exit(1)
    if not os.path.isfile(MODEL_PATH):
        print(f"[ERROR] Model not found at: {MODEL_PATH}")
        print("        Download with: huggingface-cli download microsoft/BitNet-b1.58-2B-4T-gguf "
              "--local-dir models/BitNet-b1.58-2B-4T")
        sys.exit(1)

    history = []
    print("=" * 55)
    print("  BitNet Chat — Windows 11 / Panther Lake")
    print(f"  Threads: {NUM_THREADS}  |  Model: {os.path.basename(MODEL_PATH)}")
    print("  Type 'quit' or 'exit' to stop")
    print("=" * 55)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye! 👋")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("\nGoodbye! 👋")
            break

        history.append({"role": "user", "content": user_input})

        # Build prompt from history
        prompt = ""
        for msg in history:
            if msg["role"] == "user":
                prompt += f"Human: {msg['content']}\n\nBITNETAssistant:"
            else:
                prompt += f" {msg['content']}\n\n"

        cmd = [
            LLAMA_CLI,
            "-m", MODEL_PATH,
            "-p", prompt,
            "-n", str(MAX_NEW_TOKENS),
            "-t", str(NUM_THREADS),
            "--repeat-penalty", "1.5",
            "--temp", "0.7",
            "--top-p", "0.9",
            "--no-warmup",
            "-e",
        ]

        print("\nBitNet: ", end="", flush=True)

        try:
            result = subprocess.run(cmd, capture_output=True, timeout=120)
            output = (
                result.stdout.decode("utf-8", errors="replace")
                + result.stderr.decode("utf-8", errors="replace")
            )
            response = extract_response(output)

            if response:
                if len(response) > RESPONSE_CUTOFF:
                    response = response[:RESPONSE_CUTOFF] + "..."
                print(response)
                history.append({"role": "assistant", "content": response})
            else:
                print("[No response]")

        except subprocess.TimeoutExpired:
            print("[Timeout]")
        except Exception as exc:
            print(f"[Error: {exc}]")


if __name__ == "__main__":
    chat()
