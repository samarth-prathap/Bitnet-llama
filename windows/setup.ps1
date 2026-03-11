<#
.SYNOPSIS
    Automated setup for BitNet b1.58 on Windows 11 (Panther Lake / x86-64).

.DESCRIPTION
    This script clones Microsoft BitNet, downloads the 2B model, and builds the
    project with AVX-512 / AMX support for Intel Panther Lake (or any modern
    x86-64 CPU). It is the Windows equivalent of the Apple Silicon setup from:
    https://github.com/ukosoukoso/bitnet-apple-silicon-demo

    Run from a Developer PowerShell for VS 2022 with conda activated:
        conda activate bitnet-cpp
        .\setup.ps1

.NOTES
    Prerequisites
        - Visual Studio 2022 with Clang for Windows
        - Git for Windows
        - Python >= 3.9 (Miniconda recommended)
        - conda environment 'bitnet-cpp' activated
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── helper ────────────────────────────────────────────────────────────────────
function Write-Step([string]$msg) {
    Write-Host "`n==> $msg" -ForegroundColor Cyan
}

function Assert-Command([string]$cmd) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Error "Required command not found: $cmd"
        exit 1
    }
}

# ── preflight checks ──────────────────────────────────────────────────────────
Write-Step "Checking prerequisites"
Assert-Command "git"
Assert-Command "python"
Assert-Command "cmake"
Assert-Command "clang"

$pyVer = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ([version]$pyVer -lt [version]"3.9") {
    Write-Error "Python >= 3.9 required (found $pyVer)"
    exit 1
}
Write-Host "  Python $pyVer  ✅" -ForegroundColor Green

# ── 1. clone BitNet ───────────────────────────────────────────────────────────
Write-Step "Cloning Microsoft BitNet"
if (Test-Path "BitNet") {
    Write-Host "  BitNet directory already exists — skipping clone." -ForegroundColor Yellow
} else {
    git clone --recursive https://github.com/microsoft/BitNet.git
}
Set-Location BitNet

# ── 2. install Python deps ────────────────────────────────────────────────────
Write-Step "Installing Python requirements"
pip install -r requirements.txt --quiet

# ── 3. download model ─────────────────────────────────────────────────────────
Write-Step "Downloading BitNet-b1.58-2B-4T model"
$modelDir = "models\BitNet-b1.58-2B-4T"
if (Test-Path "$modelDir\ggml-model-i2_s.gguf") {
    Write-Host "  Model already downloaded — skipping." -ForegroundColor Yellow
} else {
    huggingface-cli download microsoft/BitNet-b1.58-2B-4T-gguf `
        --local-dir $modelDir
}

# ── 4. build ──────────────────────────────────────────────────────────────────
Write-Step "Building BitNet (AVX-512 / AMX auto-detected)"
python setup_env.py -md $modelDir -q i2_s

# ── 5. verify ─────────────────────────────────────────────────────────────────
Write-Step "Verifying build"
$llamaCli = "build\bin\Release\llama-cli.exe"
if (-not (Test-Path $llamaCli)) {
    # Some builds output to build\bin\ directly
    $llamaCli = "build\bin\llama-cli.exe"
}

if (Test-Path $llamaCli) {
    $versionOutput = & $llamaCli --version 2>&1 | Select-String "AVX|system_info" | Select-Object -First 5
    Write-Host "`n  llama-cli version info:" -ForegroundColor Green
    $versionOutput | ForEach-Object { Write-Host "    $_" }
} else {
    Write-Warning "llama-cli.exe not found at expected path. Check build output above."
}

# ── 6. smoke test ─────────────────────────────────────────────────────────────
Write-Step "Running smoke test (5 tokens)"
if (Test-Path $llamaCli) {
    $modelFile = "$modelDir\ggml-model-i2_s.gguf"
    $cores     = (Get-CimInstance Win32_Processor).NumberOfCores
    & $llamaCli -m $modelFile -p "Hello" -n 5 -t $cores 2>&1 | Select-Object -Last 10
}

# ── done ──────────────────────────────────────────────────────────────────────
Write-Host "`n" + ("=" * 55) -ForegroundColor Green
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "  Run the chat interface:" -ForegroundColor Green
Write-Host "    python ..\windows\chat.py" -ForegroundColor Yellow
Write-Host ("=" * 55) -ForegroundColor Green
