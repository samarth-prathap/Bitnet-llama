# Bitnet-llama

Run Microsoft's **BitNet b1.58 2B** 1-bit LLM locally — on both
**Apple Silicon (macOS)** and **Windows 11 (Panther Lake / x86-64)** —
without a GPU.

## Platform Support

| Setup | Platform | Status |
|---|---|---|
| [**windows/**](windows/) | Windows 11 (Intel Panther Lake / AVX-512 / AMX) | ✅ Ready |
| [Apple Silicon demo](https://github.com/ukosoukoso/bitnet-apple-silicon-demo) | macOS (M1/M2/M3/M4) | ✅ (external) |

## Windows 11 — Panther Lake Quick Start

See **[windows/README.md](windows/README.md)** for the full guide.

**TL;DR** — from a Developer PowerShell for VS 2022:

```powershell
# 1. Clone BitNet
git clone --recursive https://github.com/microsoft/BitNet.git
cd BitNet

# 2. Install deps & build
pip install -r requirements.txt
huggingface-cli download microsoft/BitNet-b1.58-2B-4T-gguf --local-dir models/BitNet-b1.58-2B-4T
python setup_env.py -md models/BitNet-b1.58-2B-4T -q i2_s

# 3. Run inference
build\bin\Release\llama-cli.exe -m models\BitNet-b1.58-2B-4T\ggml-model-i2_s.gguf `
    -p "Hello" -n 50 -t 8
```

## Why Panther Lake?

Apple Silicon has **NEON** (ARM SIMD). Intel Panther Lake has
**AVX-512 + AMX** (x86-64 SIMD + matrix extensions) — BitNet's x86 kernels
already achieve **2.37×–6.17× speedup**, matching or exceeding the ARM numbers.

| | Apple Silicon | Panther Lake |
|---|---|---|
| SIMD | ARM NEON | AVX-512 / AMX |
| BitNet speedup | 1.37×–5.07× | 2.37×–6.17× |
| NPU | Apple Neural Engine | Intel NPU (~47 TOPS) |
| BitNet kernel | TL1 | TL2 / I2\_S |

## Files

```
windows/
  README.md       — full Windows 11 setup guide
  setup.ps1       — automated PowerShell setup script
  chat.py         — multi-turn chat (Windows paths, auto thread-count)
  check_cpu.py    — CPU feature checker (AVX2/AVX-512/AMX/NPU)
Sample.py         — quick inference example (Windows)
```

## Credits

- [Microsoft BitNet](https://github.com/microsoft/BitNet)
- [Apple Silicon BitNet demo](https://github.com/ukosoukoso/bitnet-apple-silicon-demo)

## License

MIT
