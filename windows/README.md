# BitNet on Windows 11 (Intel Panther Lake Ultra 9)

Run Microsoft's BitNet b1.58 2B 1-bit LLM natively on Windows 11 with Intel Panther Lake Ultra 9. Leverages AVX2, AVX-512, and AMX (Advanced Matrix Extensions) for high-throughput 1-bit inference — no patches required.

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| **Python** | 3.10+ | [python.org](https://www.python.org/downloads/) or `winget install Python.Python.3.11` |
| **Visual Studio 2022 Build Tools** | 17.x+ | [visualstudio.microsoft.com](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022) — select **Desktop development with C++** workload |
| **CMake** | 3.22+ | Included with VS Build Tools or `winget install Kitware.CMake` |
| **Git** | any | [git-scm.com](https://git-scm.com/) or `winget install Git.Git` |
| **huggingface-cli** | any | `pip install huggingface_hub` |

> **Tip:** Run `python windows\check_cpu.py` first to verify AVX2, AVX-512, and AMX support on your CPU.

## Step-by-Step Setup

### 1. Clone BitNet

Open a **Developer PowerShell for VS 2022** (or a regular PowerShell with `vcvarsall.bat` in scope):

```powershell
git clone --recursive https://github.com/microsoft/BitNet.git
cd BitNet
```

### 2. Install Python dependencies

```powershell
pip install -r requirements.txt
```

### 3. Download the model

```powershell
huggingface-cli download microsoft/BitNet-b1.58-2B-4T-gguf --local-dir models\BitNet-b1.58-2B-4T
```

### 4. Build with MSVC

```powershell
python setup_env.py -md models\BitNet-b1.58-2B-4T -q i2_s
```

`setup_env.py` calls CMake with the MSVC toolchain. BitNet's CMakeLists automatically detects and enables AVX2 / AVX-512 / AMX on Panther Lake.

### 5. Verify the build

```powershell
.\build\bin\Release\llama-cli.exe -m models\BitNet-b1.58-2B-4T\ggml-model-i2_s.gguf -p "Hello" -n 50 -t 16
```

Expected output includes a line like:

```
system_info: AVX = 1 | AVX2 = 1 | AVX512 = 1 | AVX512_VNNI = 1 | AMX_INT8 = 1 | ...
```

### 6. Multi-turn chat

Copy (or run) `chat.py` from this directory inside your `BitNet/` folder:

```powershell
# From inside the BitNet/ directory
python ..\path\to\windows\chat.py
```

Or use the automated setup script which copies everything for you:

```powershell
.\setup.ps1
```

## Intel Panther Lake Ultra 9 — CPU Features

Panther Lake Ultra 9 brings a significant jump in AI/matrix workload performance:

| Feature | What it does | Impact on BitNet |
|---------|-------------|------------------|
| **AVX2** | 256-bit integer SIMD | Baseline — always enabled |
| **AVX-512 (VNNI/BF16/IFMA)** | 512-bit SIMD with neural-net dot products | ~2× throughput vs AVX2 |
| **AMX-INT8 / AMX-BF16** | Tile-based matrix multiply (up to 1 TMAC/cycle) | Best for 1-bit weight matmul |
| **Intel NPU (AI Boost)** | Dedicated neural accelerator (Copilot+ PC) | Future offload path; not yet used by llama.cpp |

On Panther Lake, llama.cpp's GGML backend selects the highest available SIMD tier at runtime,
so no manual CMake flags are needed for correctness — the binary self-detects.

### Why no patch is needed (vs macOS)

The macOS version required patching `sysctlbyname("hw.optional.AdvSIMD", ...)` because that
sysctl key incorrectly returned 0 on Apple Silicon. On Windows/x86-64, SIMD feature detection
uses the standard **CPUID** instruction which always returns accurate results. llama.cpp's
`ggml_cpu_has_avx2()` etc. call CPUID internally — no bug, no patch needed.

## Automated Setup

Use the included PowerShell script for a fully automated setup:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned   # one-time
.\setup.ps1
```

The script will:
1. Check all prerequisites
2. Clone BitNet recursively
3. Download the model from HuggingFace
4. Build with `setup_env.py`
5. Run a smoke-test inference

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `cmake` not found | Install VS 2022 Build Tools with **C++ workload**, or `winget install Kitware.CMake` |
| `huggingface-cli` not found | `pip install huggingface_hub` |
| `llama-cli.exe` not found after build | Check `build\bin\Release\` — MSVC puts binaries in a `Release\` subfolder |
| Slow performance / AVX-512 disabled | Ensure you are building with MSVC, not MinGW — MinGW may not enable all AVX-512 extensions |
| `AMX_INT8 = 0` in system_info | AMX requires Windows 11 22H2+ and an Intel 12th-gen+ CPU with AMX support |
