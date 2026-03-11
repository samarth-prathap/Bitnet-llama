#!/usr/bin/env python3
"""
Sample inference script for BitNet b1.58 on Windows 11 (x86-64 / Panther Lake).

Usage (from your BitNet directory, after running windows/setup.ps1):
    python Sample.py
    python Sample.py --prompt "Explain 1-bit LLMs" --tokens 100
"""

import argparse
import os
import subprocess
import sys


MODEL_PATH = r"models\BitNet-b1.58-2B-4T\ggml-model-i2_s.gguf"
LLAMA_CLI  = r"build\bin\Release\llama-cli.exe"


def _find_llama_cli(override: str = "") -> str:
    if override and os.path.isfile(override):
        return override
    for candidate in [
        r"build\bin\Release\llama-cli.exe",
        r"build\bin\llama-cli.exe",
        r"build\bin\Debug\llama-cli.exe",
    ]:
        if os.path.isfile(candidate):
            return candidate
    return LLAMA_CLI


def _physical_cores() -> int:
    try:
        import psutil
        return psutil.cpu_count(logical=False) or os.cpu_count() or 8
    except ImportError:
        return os.cpu_count() or 8


def run_inference(prompt: str, n_tokens: int = 50, threads: int = 0,
                  model: str = "", cli: str = "") -> None:
    llama_cli  = _find_llama_cli(cli)
    model_path = model or MODEL_PATH
    num_threads = threads or _physical_cores()

    if not os.path.isfile(llama_cli):
        print(f"[ERROR] llama-cli not found at: {llama_cli}")
        print("        Run windows/setup.ps1 first.")
        sys.exit(1)

    if not os.path.isfile(model_path):
        print(f"[ERROR] Model not found at: {model_path}")
        print("        Download with:")
        print("        huggingface-cli download microsoft/BitNet-b1.58-2B-4T-gguf "
              "--local-dir models/BitNet-b1.58-2B-4T")
        sys.exit(1)

    cmd = [
        llama_cli,
        "-m", model_path,
        "-p", prompt,
        "-n", str(n_tokens),
        "-t", str(num_threads),
    ]

    print(f"Running BitNet inference on {num_threads} threads...")
    print(f"Prompt: {prompt!r}\n")
    print("-" * 50)

    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        print(f"\n[WARN] llama-cli exited with code {result.returncode}")


def main():
    parser = argparse.ArgumentParser(
        description="Sample BitNet inference on Windows 11 / Panther Lake"
    )
    parser.add_argument("--prompt",  default="The future of AI on local devices is",
                        help="Prompt text")
    parser.add_argument("--tokens",  type=int, default=50,
                        help="Number of tokens to generate (default: 50)")
    parser.add_argument("--threads", type=int, default=0,
                        help="Thread count (0 = auto-detect physical cores)")
    parser.add_argument("--model",   default="",
                        help="Path to GGUF model file")
    parser.add_argument("--cli",     default="",
                        help="Path to llama-cli.exe")
    args = parser.parse_args()

    run_inference(
        prompt=args.prompt,
        n_tokens=args.tokens,
        threads=args.threads,
        model=args.model,
        cli=args.cli,
    )


if __name__ == "__main__":
    main()
