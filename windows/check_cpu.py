#!/usr/bin/env python3
"""
CPU Feature Checker for BitNet on Windows 11 (Panther Lake / x86-64)
Checks for AVX2, AVX-512, AMX, and NPU availability.
"""

import subprocess
import sys
import platform
import struct

def check_python():
    print(f"Python:   {sys.version}")
    print(f"Platform: {platform.platform()}")
    print(f"Machine:  {platform.machine()}")
    print()

def cpuid(leaf, subleaf=0):
    """Run CPUID via a small inline approach using cpuinfo if available."""
    try:
        import cpuinfo  # py-cpuinfo
        return None, cpuinfo.get_cpu_info()
    except ImportError:
        return None, None

def check_features_via_cpuinfo():
    """Use py-cpuinfo to detect CPU flags."""
    try:
        import cpuinfo
        info = cpuinfo.get_cpu_info()
        flags = info.get("flags", [])
        brand  = info.get("brand_raw", "Unknown CPU")
        hz     = info.get("hz_advertised_friendly", "?")

        print(f"CPU:      {brand}")
        print(f"Speed:    {hz}")
        print()

        features = {
            "AVX":        "avx"       in flags,
            "AVX2":       "avx2"      in flags,
            "AVX-512F":   "avx512f"   in flags,
            "AVX-512BW":  "avx512bw"  in flags,
            "AVX-512VL":  "avx512vl"  in flags,
            "AVX-512VNNI":"avx512vnni" in flags,
            "AMX-BF16":   "amx_bf16"  in flags,
            "AMX-INT8":   "amx_int8"  in flags,
            "AMX-TILE":   "amx_tile"  in flags,
            "FMA":        "fma"       in flags,
            "F16C":       "f16c"      in flags,
        }

        print("Detected CPU features:")
        for feat, present in features.items():
            status = "✅" if present else "❌"
            print(f"  {status} {feat}")

        print()
        return features
    except ImportError:
        print("py-cpuinfo not installed. Run: pip install py-cpuinfo")
        return {}

def check_npu_windows():
    """Check for NPU (Neural Processing Unit) on Windows via WMI / DirectML."""
    print("NPU / Accelerator detection:")

    # Try PowerShell query for NPU-like devices
    ps_cmd = [
        "powershell", "-NoProfile", "-Command",
        "Get-PnpDevice | Where-Object { $_.Class -eq 'System' -or $_.FriendlyName -match 'NPU|Neural|VPU|GNA' } "
        "| Select-Object FriendlyName, Status | Format-Table -AutoSize"
    ]
    try:
        result = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=15)
        if result.stdout.strip():
            print(result.stdout)
        else:
            print("  No NPU device found via PnpDevice (may require Panther Lake hardware).")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("  PowerShell not available or timed out. Skipping NPU check.")

    # Check for Intel OpenVINO or DirectML
    try:
        import openvino
        print(f"  ✅ OpenVINO {openvino.__version__} detected (can target NPU)")
    except ImportError:
        print("  ❌ OpenVINO not installed (optional — enables NPU inference)")

    try:
        import torch_directml  # type: ignore
        print(f"  ✅ torch-directml detected (DirectML GPU/NPU backend)")
    except ImportError:
        print("  ❌ torch-directml not installed (optional)")

    print()

def summarize(features):
    """Print a BitNet optimisation summary."""
    avx2    = features.get("AVX2", False)
    avx512  = features.get("AVX-512F", False)
    amx     = features.get("AMX-INT8", False) or features.get("AMX-TILE", False)

    print("=" * 55)
    print("  BitNet Performance Summary")
    print("=" * 55)

    if avx512 and amx:
        tier = "🚀 EXCELLENT (Panther Lake / Meteor Lake / Sapphire Rapids)"
        quant = "i2_s or tl2  (AVX-512 + AMX kernels)"
        threads_hint = "Use -t equal to physical core count"
    elif avx512:
        tier = "✅ GREAT (AVX-512 capable CPU)"
        quant = "i2_s or tl2  (AVX-512 kernels)"
        threads_hint = "Use -t equal to physical core count"
    elif avx2:
        tier = "✅ GOOD (AVX2 capable CPU)"
        quant = "i2_s  (AVX2 kernels)"
        threads_hint = "Use -t equal to physical core count"
    else:
        tier = "⚠️  BASIC (no AVX2 — performance will be limited)"
        quant = "i2_s  (scalar/SSE fallback)"
        threads_hint = "Use -t equal to physical core count"

    print(f"  Performance tier : {tier}")
    print(f"  Recommended quant: {quant}")
    print(f"  Threading hint   : {threads_hint}")
    print("=" * 55)

if __name__ == "__main__":
    print("=" * 55)
    print("  BitNet CPU Feature Checker — Windows 11")
    print("  Panther Lake / x86-64 Edition")
    print("=" * 55)
    print()
    check_python()
    features = check_features_via_cpuinfo()
    check_npu_windows()
    summarize(features)
