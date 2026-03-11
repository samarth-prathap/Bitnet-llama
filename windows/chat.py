#!/usr/bin/env python3
"""
windows/chat.py — Multi-turn chat script for BitNet on Windows 11.

Windows-adapted version of the macOS chat script from
https://github.com/ukosoukoso/bitnet-apple-silicon-demo

Usage (run from inside your BitNet/ clone directory):
    python windows\\chat.py

The script auto-detects the model and llama-cli.exe paths relative to the
current working directory (expected to be the BitNet repo root).
"""

import subprocess
import sys
import re
import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Path configuration — Windows uses .exe and Release/ sub-directory
# ---------------------------------------------------------------------------

def find_llama_cli() -> Path:
    """Locate llama-cli.exe in the BitNet build output directory."""
    candidates = [
        Path("build") / "bin" / "Release" / "llama-cli.exe",
        Path("build") / "bin" / "llama-cli.exe",          # cmake --config Debug
        Path("build") / "bin" / "Debug" / "llama-cli.exe",
    ]
    for path in candidates:
        if path.exists():
            return path
    # Fall back to PATH lookup
    return Path("llama-cli.exe")


def find_model() -> Path:
    """Locate the default BitNet GGUF model file."""
    default = Path("models") / "BitNet-b1.58-2B-4T" / "ggml-model-i2_s.gguf"
    if default.exists():
        return default
    # Search for any .gguf file under models/
    for p in Path("models").rglob("*.gguf"):
        return p
    return default


MODEL_PATH = find_model()
LLAMA_CLI = find_llama_cli()


# ---------------------------------------------------------------------------
# Response parsing (same logic as macOS version, platform-neutral)
# ---------------------------------------------------------------------------

def extract_response(output: str) -> str:
    """Extract the assistant's generated text from llama-cli output.

    llama-cli writes both the prompt and the generated continuation to stdout,
    interleaved with logging lines.  We strip the logging noise and isolate
    the model's response.
    """
    lines = output.split("\n")
    filtered: list[str] = []
    skip_prefixes = (
        "llama_", "ggml_", "llm_load", "main:", "build:", "sampler",
        "generate:", "common_", "check_double", "\t", "system_info",
    )

    in_output = False
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

    # The prompt ends with "BITNETAssistant:" — grab everything after the last one.
    if "BITNETAssistant:" in text:
        text = text.split("BITNETAssistant:")[-1].strip()

    # Clean up sentinel tokens / trailing prompt artefacts.
    text = text.replace("[end of text]", "").strip()
    text = re.sub(r"\s*Human:\s*$", "", text)

    return text


# ---------------------------------------------------------------------------
# Chat loop
# ---------------------------------------------------------------------------

def chat() -> None:
    """Run an interactive multi-turn chat session with the BitNet model."""
    if not LLAMA_CLI.exists():
        print(f"[ERROR] llama-cli.exe not found at '{LLAMA_CLI}'.")
        print("        Build BitNet first:  python setup_env.py -md models\\BitNet-b1.58-2B-4T -q i2_s")
        sys.exit(1)

    if not MODEL_PATH.exists():
        print(f"[ERROR] Model not found at '{MODEL_PATH}'.")
        print("        Download it:  huggingface-cli download microsoft/BitNet-b1.58-2B-4T-gguf "
              "--local-dir models\\BitNet-b1.58-2B-4T")
        sys.exit(1)

    history: list[dict] = []

    print("=" * 55)
    print("  BitNet Multi-Turn Chat  (Windows / Panther Lake)")
    print(f"  Model : {MODEL_PATH}")
    print(f"  Exe   : {LLAMA_CLI}")
    print("  Type 'quit' or 'exit' to stop, Ctrl+C to abort.")
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

        # Build prompt from conversation history (same template as macOS version).
        prompt = ""
        for msg in history:
            if msg["role"] == "user":
                prompt += f"Human: {msg['content']}\n\nBITNETAssistant:"
            else:
                prompt += f" {msg['content']}\n\n"

        cmd = [
            str(LLAMA_CLI),
            "-m", str(MODEL_PATH),
            "-p", prompt,
            "-n", "200",
            "-t", str(os.cpu_count() or 8),  # use all logical cores
            "--repeat-penalty", "1.5",
            "--temp", "0.7",
            "--top-p", "0.9",
            "--no-warmup",
            "-e",  # process escape sequences
        ]

        print("\nBitNet: ", end="", flush=True)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=120,
            )
            output = (
                result.stdout.decode("utf-8", errors="replace")
                + result.stderr.decode("utf-8", errors="replace")
            )
            response = extract_response(output)

            if response:
                if len(response) > 1000:
                    response = response[:1000] + "..."
                print(response)
                history.append({"role": "assistant", "content": response})
            else:
                print("[no response]")

        except subprocess.TimeoutExpired:
            print("[timeout — model took too long]")
        except FileNotFoundError:
            print(f"[ERROR] Could not launch '{LLAMA_CLI}'. Is the build complete?")
        except Exception as exc:  # noqa: BLE001
            print(f"[error: {exc}]")


if __name__ == "__main__":
    chat()
