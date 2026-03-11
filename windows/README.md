# BitNet on Windows 11 — Panther Lake Edition

Run Microsoft's **BitNet b1.58 2B** model natively on Windows 11 with Intel
**Panther Lake** (or any modern x86-64 CPU with AVX2 / AVX-512 / AMX).

This is the Windows 11 equivalent of the
[Apple Silicon BitNet demo](https://github.com/ukosoukoso/bitnet-apple-silicon-demo).

---

## Platform Comparison

| Feature | Apple Silicon (macOS) | Intel Panther Lake (Windows 11) |
|---|---|---|
| SIMD | ARM NEON | AVX2 / AVX-512 / AMX |
| Kernel | TL1 | TL2 / I2\_S |
| BitNet speedup | 1.37×–5.07× | 2.37×–6.17× |
| Build toolchain | Xcode CLT / clang | Visual Studio 2022 + Clang |
| NPU | Apple Neural Engine | Intel NPU (OpenVINO / DirectML) |

---

## Why Panther Lake?

Intel **Panther Lake** (Core Ultra 200V / next-gen mobile, 2025–2026) brings:

* **AVX-512** back to mobile (dropped in Raptor Lake, restored here)
* **AMX** (Advanced Matrix Extensions) — hardware tile-based matrix ops
* **Intel NPU** with ~40–47 TOPS for AI inference
* Full **Windows 11 24H2** support

BitNet on x86 already achieves **2.37×–6.17× speedup** with AVX-512 kernels,
matching or beating the Apple Silicon numbers for the same model size.

---

## Quick Start

### Prerequisites

Open **Developer Command Prompt / PowerShell for VS 2022** for all steps.

```
Required:
  - Windows 11 (22H2 or later)
  - Visual Studio 2022  (Desktop C++, CMake, Clang for Windows)
  - Git for Windows
  - Python >= 3.9  (Miniconda recommended)
  - CMake >= 3.22
```

Install Python deps:

```powershell
conda create -n bitnet-cpp python=3.9
conda activate bitnet-cpp
pip install huggingface_hub
```

### 1. Clone BitNet

```powershell
git clone --recursive https://github.com/microsoft/BitNet.git
cd BitNet
```

### 2. Install requirements

```powershell
pip install -r requirements.txt
```

### 3. Download the model

```powershell
huggingface-cli download microsoft/BitNet-b1.58-2B-4T-gguf `
    --local-dir models/BitNet-b1.58-2B-4T
```

### 4. Build with AVX-512 support

```powershell
python setup_env.py -md models/BitNet-b1.58-2B-4T -q i2_s
```

> **Tip for Panther Lake / AVX-512 CPUs:** the build system auto-detects
> AVX-512 via CPUID — no patch needed (unlike the NEON fix required on macOS).
> Verify after building:
>
> ```
> build\bin\Release\llama-cli.exe --version
> # should show: AVX = 1 | AVX2 = 1 | AVX512 = 1 | AMX_INT8 = 1
> ```

### 5. Run inference

```powershell
build\bin\Release\llama-cli.exe `
    -m models/BitNet-b1.58-2B-4T/ggml-model-i2_s.gguf `
    -p "Hello, what can you do?" `
    -n 50 `
    -t 8
```

### 6. Interactive chat

Copy `chat.py` to your BitNet directory and run:

```powershell
python chat.py
```

---

## Automated Setup

For a one-shot setup, run the provided PowerShell script
(from the cloned BitNet directory):

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
..\windows\setup.ps1
```

---

## CPU Feature Check

Before building, verify your CPU's SIMD capabilities:

```powershell
pip install py-cpuinfo
python check_cpu.py
```

Expected output on Panther Lake:

```
  ✅ AVX
  ✅ AVX2
  ✅ AVX-512F
  ✅ AVX-512BW
  ✅ AVX-512VL
  ✅ AVX-512VNNI
  ✅ AMX-BF16
  ✅ AMX-INT8
  ✅ AMX-TILE
  ✅ FMA
  ✅ F16C
```

---

## Benchmark (expected on Panther Lake)

| Metric | Value |
|---|---|
| Model | BitNet b1.58 2B (I2\_S) |
| Size | ~1.1 GiB |
| AVX-512 | ✅ Enabled |
| AMX | ✅ Enabled |
| Speed (est.) | 30–80 tokens/sec (varies by core count) |

> Numbers are estimates based on Microsoft's published x86 benchmarks.
> Actual Panther Lake results will vary; the AVX-512 re-introduction should
> restore perf parity with Apple Silicon for this workload.

---

## Troubleshooting

### `AVX512 = 0` in system_info

* Ensure you built with the VS 2022 Clang toolchain, not MSVC-only.
* Run `build\bin\Release\llama-cli.exe --version` to verify.
* If using an older CPU that lacks AVX-512, use `i2_s` with AVX2 (still fast).

### Build fails with "clang not found"

Install **C++-Clang Compiler for Windows** and
**MS-Build Support for LLVM-Toolset (clang)** via the VS 2022 installer.

### `huggingface-cli` not found

```powershell
pip install huggingface_hub
```

---

## Credits

* [Microsoft BitNet](https://github.com/microsoft/BitNet)
* [Apple Silicon BitNet demo](https://github.com/ukosoukoso/bitnet-apple-silicon-demo)
  (inspiration for this Windows guide)

## License

MIT (same as BitNet)
