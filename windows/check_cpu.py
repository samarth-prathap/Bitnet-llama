#!/usr/bin/env python3
"""
windows/check_cpu.py — CPU feature detection for BitNet on Windows 11.

Detects AVX2, AVX-512, AMX (Advanced Matrix Extensions) and Intel NPU
presence on Windows x86-64 systems.  Prints a summary table similar to the
system_info line emitted by llama.cpp:

    system_info: AVX = 1 | AVX2 = 1 | AVX512 = 1 | AMX_INT8 = 1 | ...

Usage:
    python windows\\check_cpu.py

Works on Python 3.10+ on Windows 11.  The CPUID-based checks also work on
Linux/macOS for testing, but NPU detection is Windows-only (uses PowerShell).
"""

import ctypes
import ctypes.util
import os
import platform
import subprocess
import struct
import sys
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# CPUID helper
# ---------------------------------------------------------------------------

def _cpuid(leaf: int, subleaf: int = 0) -> tuple[int, int, int, int]:
    """Execute the CPUID instruction and return (eax, ebx, ecx, edx).

    Uses inline machine code via ctypes on Windows x86-64.  Falls back to
    zeros if the platform is not x86-64 or the call fails.
    """
    if platform.machine().lower() not in ("amd64", "x86_64", "x86"):
        return 0, 0, 0, 0

    try:
        # 64-byte buffer: [eax_in, ecx_in, eax_out, ebx_out, ecx_out, edx_out]
        buf = (ctypes.c_uint32 * 6)(leaf, subleaf, 0, 0, 0, 0)

        # Minimal x86-64 shellcode: push regs, cpuid, store results, pop regs, ret
        # mov eax,[rcx]; mov r8,rcx; mov ecx,[rcx+4];
        # cpuid;
        # mov [r8+8],eax; mov [r8+12],ebx; mov [r8+16],ecx; mov [r8+20],edx; ret
        shellcode = bytes([
            0x8B, 0x01,                    # mov eax, [rcx]
            0x49, 0x89, 0xC8,              # mov r8, rcx
            0x8B, 0x49, 0x04,              # mov ecx, [rcx+4]
            0x53,                          # push rbx
            0x0F, 0xA2,                    # cpuid
            0x41, 0x89, 0x40, 0x08,        # mov [r8+8], eax
            0x41, 0x89, 0x58, 0x0C,        # mov [r8+12], ebx
            0x41, 0x89, 0x48, 0x10,        # mov [r8+16], ecx
            0x41, 0x89, 0x50, 0x14,        # mov [r8+20], edx
            0x5B,                          # pop rbx
            0xC3,                          # ret
        ])

        size = len(shellcode)

        if sys.platform == "win32":
            # VirtualAlloc with PAGE_EXECUTE_READWRITE
            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            MEM_COMMIT = 0x1000
            PAGE_EXECUTE_READWRITE = 0x40
            mem = kernel32.VirtualAlloc(None, size, MEM_COMMIT, PAGE_EXECUTE_READWRITE)
            if not mem:
                raise OSError("VirtualAlloc failed")
            ctypes.memmove(mem, shellcode, size)
            func = ctypes.CFUNCTYPE(None, ctypes.POINTER(ctypes.c_uint32))(mem)
            func(buf)
            kernel32.VirtualFree(mem, 0, 0x8000)  # MEM_RELEASE
        else:
            # On Linux/macOS for testing: use mmap
            import mmap
            mm = mmap.mmap(-1, size, prot=mmap.PROT_READ | mmap.PROT_WRITE | mmap.PROT_EXEC)
            mm.write(shellcode)
            mm.seek(0)
            addr = ctypes.addressof((ctypes.c_char * size).from_buffer(mm))
            func = ctypes.CFUNCTYPE(None, ctypes.POINTER(ctypes.c_uint32))(addr)
            func(buf)

        return int(buf[2]), int(buf[3]), int(buf[4]), int(buf[5])

    except Exception:  # noqa: BLE001 — any failure → assume feature absent
        return 0, 0, 0, 0


# ---------------------------------------------------------------------------
# Feature detection
# ---------------------------------------------------------------------------

@dataclass
class CpuFeatures:
    """Container for detected CPU features."""

    cpu_brand: str = ""
    avx: bool = False
    avx2: bool = False
    avx512f: bool = False
    avx512bw: bool = False
    avx512vl: bool = False
    avx512vnni: bool = False
    avx512bf16: bool = False
    avx512ifma: bool = False
    amx_tile: bool = False
    amx_int8: bool = False
    amx_bf16: bool = False
    f16c: bool = False
    fma: bool = False
    npu_present: bool = False
    npu_name: str = ""
    warnings: list[str] = field(default_factory=list)


def detect_features() -> CpuFeatures:
    """Query CPUID and Windows APIs to populate a CpuFeatures instance."""
    feat = CpuFeatures()

    # ----- Leaf 0x80000002-4: CPU brand string -----
    brand_parts: list[str] = []
    for leaf in (0x80000002, 0x80000003, 0x80000004):
        regs = _cpuid(leaf)
        for reg in regs:
            brand_parts.append(struct.pack("<I", reg).decode("ascii", errors="replace"))
    feat.cpu_brand = "".join(brand_parts).strip("\x00").strip()

    # ----- Leaf 1: basic features (ecx / edx) -----
    _, _, ecx1, _ = _cpuid(1)
    feat.avx   = bool(ecx1 & (1 << 28))
    feat.f16c  = bool(ecx1 & (1 << 29))
    feat.fma   = bool(ecx1 & (1 << 12))

    # ----- Leaf 7 sub-leaf 0: extended features (ebx / ecx / edx) -----
    _, ebx7, ecx7, edx7 = _cpuid(7, 0)
    feat.avx2         = bool(ebx7 & (1 << 5))
    feat.avx512f      = bool(ebx7 & (1 << 16))
    feat.avx512bw     = bool(ebx7 & (1 << 30))
    feat.avx512vl     = bool(ebx7 & (1 << 31))
    feat.avx512vnni   = bool(ecx7 & (1 << 11))
    feat.avx512ifma   = bool(ebx7 & (1 << 21))
    feat.amx_tile     = bool(edx7 & (1 << 24))
    feat.amx_int8     = bool(edx7 & (1 << 25))
    feat.amx_bf16     = bool(edx7 & (1 << 22))

    # ----- Leaf 7 sub-leaf 1: AVX-512 BF16 -----
    _, _, ecx71, _ = _cpuid(7, 1)
    feat.avx512bf16 = bool(ecx71 & (1 << 5))

    # ----- NPU detection via PowerShell (Windows only) -----
    if sys.platform == "win32":
        feat.npu_present, feat.npu_name = _detect_npu_windows()

    # ----- Sanity warnings -----
    if feat.amx_tile and not feat.amx_int8 and not feat.amx_bf16:
        feat.warnings.append(
            "AMX tile support detected but AMX-INT8/BF16 not set — OS may need enabling via XSAVE."
        )
    if feat.avx512f and not feat.avx2:
        feat.warnings.append("AVX-512 without AVX2 — unexpected; CPUID read may have failed.")

    return feat


def _detect_npu_windows() -> tuple[bool, str]:
    """Use PowerShell/WMI to check for an Intel NPU device on Windows."""
    try:
        ps_script = (
            "Get-PnpDevice | "
            "Where-Object { $_.FriendlyName -match 'Intel.*NPU|Intel.*Neural|Intel.*AI Boost|Intel.*VPU' -and "
            "$_.Status -eq 'OK' } | "
            "Select-Object -First 1 -ExpandProperty FriendlyName"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=10,
        )
        name = result.stdout.strip()
        if name:
            return True, name
    except Exception:  # noqa: BLE001
        pass
    return False, ""


# ---------------------------------------------------------------------------
# Pretty-print summary
# ---------------------------------------------------------------------------

_YES = "\033[32m1\033[0m"   # green 1
_NO  = "\033[31m0\033[0m"   # red   0


def _flag(value: bool) -> str:
    return _YES if value else _NO


def print_summary(feat: CpuFeatures) -> None:
    """Print a summary table modelled on llama.cpp's system_info line."""
    print()
    print("=" * 60)
    print("  CPU Feature Check — BitNet / Windows 11 (Panther Lake)")
    print("=" * 60)
    print(f"  CPU   : {feat.cpu_brand or '(unknown)'}")
    print(f"  OS    : {platform.system()} {platform.version()}")
    print()

    # llama.cpp-style one-liner
    flags = [
        f"AVX = {_flag(feat.avx)}",
        f"AVX2 = {_flag(feat.avx2)}",
        f"FMA = {_flag(feat.fma)}",
        f"F16C = {_flag(feat.f16c)}",
        f"AVX512 = {_flag(feat.avx512f)}",
        f"AVX512_BW = {_flag(feat.avx512bw)}",
        f"AVX512_VL = {_flag(feat.avx512vl)}",
        f"AVX512_VNNI = {_flag(feat.avx512vnni)}",
        f"AVX512_BF16 = {_flag(feat.avx512bf16)}",
        f"AMX_TILE = {_flag(feat.amx_tile)}",
        f"AMX_INT8 = {_flag(feat.amx_int8)}",
        f"AMX_BF16 = {_flag(feat.amx_bf16)}",
    ]
    print("  system_info: " + " | ".join(flags))
    print()

    # NPU row
    if feat.npu_present:
        print(f"  NPU   : \033[32mDetected\033[0m — {feat.npu_name}")
    else:
        print("  NPU   : \033[33mNot detected\033[0m (Intel AI Boost / VPU not found or not on Windows)")

    print()

    # Recommendations
    print("  Recommendations:")
    if feat.amx_int8:
        print("  \033[32m✓\033[0m AMX-INT8 detected — optimal for 1-bit integer matmul (best performance)")
    elif feat.avx512vnni:
        print("  \033[33m~\033[0m AVX-512 VNNI detected — good for 1-bit inference (no AMX, but still fast)")
    elif feat.avx512f:
        print("  \033[33m~\033[0m AVX-512F detected — solid baseline performance")
    elif feat.avx2:
        print("  \033[33m~\033[0m AVX2 detected — BitNet will run correctly; consider a CPU with AVX-512/AMX for best speed")
    else:
        print("  \033[31m✗\033[0m AVX2 not detected — BitNet may fall back to scalar code (slow)")

    if feat.npu_present:
        print("  \033[32m✓\033[0m Intel NPU detected — future llama.cpp releases may offload ops to the NPU")

    # Warnings
    for w in feat.warnings:
        print(f"  \033[33m⚠\033[0m {w}")

    print()
    print("=" * 60)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Main entry point."""
    feat = detect_features()
    print_summary(feat)

    # Exit code: 0 if AVX2 available (minimum for BitNet), 1 otherwise.
    sys.exit(0 if feat.avx2 else 1)


if __name__ == "__main__":
    main()
