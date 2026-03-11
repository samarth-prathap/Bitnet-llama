# BitNet 1-Bit LLM on Windows 11 (Intel Panther Lake)

Running Microsoft's BitNet b1.58 2B model on Windows 11 with Intel Panther Lake Ultra 9.

> **Reference:** This project is the Windows 11 equivalent of
> [ukosoukoso/bitnet-apple-silicon-demo](https://github.com/ukosoukoso/bitnet-apple-silicon-demo)
> (Apple Silicon version).

## Choose Your Setup

| Setup | Platform | Status |
|-------|----------|--------|
| [**windows/**](./windows/) | Windows 11, Intel Panther Lake Ultra 9 | ✅ Ready |

## TL;DR — Windows 11 Quick Start

```powershell
# 1. Clone BitNet
git clone --recursive https://github.com/microsoft/BitNet.git
cd BitNet

# 2. Download model
huggingface-cli download microsoft/BitNet-b1.58-2B-4T-gguf --local-dir models/BitNet-b1.58-2B-4T

# 3. Build (requires Visual Studio 2022 Build Tools)
python setup_env.py -md models/BitNet-b1.58-2B-4T -q i2_s

# 4. Run inference
.\build\bin\Release\llama-cli.exe -m models\BitNet-b1.58-2B-4T\ggml-model-i2_s.gguf -p "Hello" -n 50 -t 16
```

Or use the automated PowerShell setup script:

```powershell
cd windows
.\setup.ps1
```

## Intel Panther Lake Ultra 9 — SIMD Acceleration

Unlike the Apple Silicon version (which needed a NEON detection patch), the x86/x86-64 SIMD
path in BitNet's llama.cpp works without modifications. Intel Panther Lake Ultra 9 brings:

| Feature | Description | Benefit for BitNet |
|---------|-------------|-------------------|
| **AVX2** | 256-bit SIMD integer ops | Baseline 1-bit inference |
| **AVX-512** | 512-bit SIMD with BF16 | 2× throughput over AVX2 |
| **AMX** | Advanced Matrix Extensions (tile-based matmul) | Optimal for 1-bit weight matmul |
| **NPU** | Neural Processing Unit (Copilot+ AI Boost) | Offload suitable workloads |

To verify your CPU features before building, run:

```powershell
python windows\check_cpu.py
```

## Benchmark (Panther Lake Ultra 9 — expected)

| Metric | Value |
|--------|-------|
| Model | BitNet b1.58 2B (I2_S) |
| Size | ~1.10 GiB |
| AVX-512 | ✅ Enabled |
| AMX | ✅ Enabled |
| Expected Speed | ~40–80+ tokens/sec (comparable to M4 Pro, potentially faster with AMX) |

> **Note:** Benchmarks are estimates based on Panther Lake's AMX/AVX-512 capabilities.
> Actual results will vary. Run `Sample.py` or `windows\chat.py` to measure on your hardware.

## macOS vs Windows Differences

| macOS (Original) | Windows 11 (This repo) |
|---|---|
| ARM NEON SIMD | AVX2 / AVX-512 / AMX |
| `sysctlbyname()` NEON bug fix required | No patch needed — x86 SIMD path works correctly |
| Homebrew (`brew install cmake`) | `winget` / Visual Studio Build Tools |
| Bash scripts | PowerShell `.ps1` scripts |
| `./build/bin/llama-cli` | `.\build\bin\Release\llama-cli.exe` |
| ~40–70 tok/s (M4 Pro, NEON) | ~40–80+ tok/s expected (Panther Lake, AMX) |

## Credits

- [Microsoft BitNet](https://github.com/microsoft/BitNet) — the 1-bit LLM framework
- [ukosoukoso/bitnet-apple-silicon-demo](https://github.com/ukosoukoso/bitnet-apple-silicon-demo) — original Apple Silicon demo this project is based on

## License

MIT (same as BitNet)
