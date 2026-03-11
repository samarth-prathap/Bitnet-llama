<#
.SYNOPSIS
    Automated setup script for BitNet on Windows 11 (Intel Panther Lake).

.DESCRIPTION
    Checks prerequisites, clones the BitNet repository, downloads the
    BitNet b1.58 2B model from HuggingFace, builds with MSVC using
    setup_env.py (i2_s quantization), and runs a smoke-test inference.

.EXAMPLE
    # One-time: allow local scripts (run in an elevated PowerShell once)
    Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

    # Then simply run:
    .\setup.ps1

.NOTES
    Requires:
      - Python 3.10+
      - Visual Studio 2022 Build Tools with Desktop C++ workload
      - CMake 3.22+ (bundled with VS or standalone)
      - Git
      - Internet access (GitHub + HuggingFace)
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Helper: colored output
# ---------------------------------------------------------------------------
function Write-Info  { param([string]$msg) Write-Host "[INFO]  $msg" -ForegroundColor Cyan }
function Write-Ok    { param([string]$msg) Write-Host "[ OK ]  $msg" -ForegroundColor Green }
function Write-Warn  { param([string]$msg) Write-Host "[WARN]  $msg" -ForegroundColor Yellow }
function Write-Fail  { param([string]$msg) Write-Host "[FAIL]  $msg" -ForegroundColor Red }

function Assert-Command {
    param([string]$Name, [string]$InstallHint)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Write-Fail "$Name not found. $InstallHint"
        exit 1
    }
    Write-Ok "$Name found."
}

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
$BITNET_REPO    = "https://github.com/microsoft/BitNet.git"
$BITNET_DIR     = "BitNet"
$MODEL_HF_REPO  = "microsoft/BitNet-b1.58-2B-4T-gguf"
$MODEL_LOCAL    = "models\BitNet-b1.58-2B-4T"
$MODEL_GGUF     = "$MODEL_LOCAL\ggml-model-i2_s.gguf"
$LLAMA_CLI      = "build\bin\Release\llama-cli.exe"  # MSVC Release artifact path
$QUANT          = "i2_s"
$NUM_THREADS    = [Environment]::ProcessorCount

Write-Host ""
Write-Host "========================================================" -ForegroundColor Magenta
Write-Host "  BitNet Windows Setup — Intel Panther Lake Ultra 9"     -ForegroundColor Magenta
Write-Host "========================================================" -ForegroundColor Magenta
Write-Host ""

# ---------------------------------------------------------------------------
# Step 1: Check prerequisites
# ---------------------------------------------------------------------------
Write-Info "Checking prerequisites..."

Assert-Command "git"    "Install from https://git-scm.com/ or: winget install Git.Git"
Assert-Command "python" "Install from https://python.org or: winget install Python.Python.3.11"
Assert-Command "cmake"  "Install VS 2022 Build Tools with C++ workload or: winget install Kitware.CMake"

# Check Python version >= 3.10
$pyVer = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$pyMajor, $pyMinor = $pyVer -split '\.' | ForEach-Object { [int]$_ }
if ($pyMajor -lt 3 -or ($pyMajor -eq 3 -and $pyMinor -lt 10)) {
    Write-Fail "Python 3.10+ required, found $pyVer."
    exit 1
}
Write-Ok "Python $pyVer"

# Check huggingface-cli
if (-not (Get-Command "huggingface-cli" -ErrorAction SilentlyContinue)) {
    Write-Info "huggingface-cli not found. Installing huggingface_hub..."
    pip install --quiet huggingface_hub
    Write-Ok "huggingface_hub installed."
}
else {
    Write-Ok "huggingface-cli found."
}

Write-Host ""

# ---------------------------------------------------------------------------
# Step 2: Clone BitNet
# ---------------------------------------------------------------------------
if (Test-Path $BITNET_DIR) {
    Write-Info "BitNet directory '$BITNET_DIR' already exists — skipping clone."
}
else {
    Write-Info "Cloning BitNet (recursive, may take a few minutes)..."
    git clone --recursive $BITNET_REPO $BITNET_DIR
    Write-Ok "BitNet cloned to '$BITNET_DIR'."
}

Set-Location $BITNET_DIR

# ---------------------------------------------------------------------------
# Step 3: Install Python dependencies
# ---------------------------------------------------------------------------
if (Test-Path "requirements.txt") {
    Write-Info "Installing Python requirements..."
    pip install --quiet -r requirements.txt
    Write-Ok "Python requirements installed."
}

# ---------------------------------------------------------------------------
# Step 4: Download the model
# ---------------------------------------------------------------------------
if (Test-Path $MODEL_GGUF) {
    Write-Info "Model already present at '$MODEL_GGUF' — skipping download."
}
else {
    Write-Info "Downloading BitNet b1.58 2B model from HuggingFace (may take several minutes)..."
    huggingface-cli download $MODEL_HF_REPO --local-dir $MODEL_LOCAL
    Write-Ok "Model downloaded to '$MODEL_LOCAL'."
}

# ---------------------------------------------------------------------------
# Step 5: Build
# ---------------------------------------------------------------------------
if (Test-Path $LLAMA_CLI) {
    Write-Info "Build artefact '$LLAMA_CLI' already exists — skipping build."
}
else {
    Write-Info "Building BitNet with MSVC (quantization: $QUANT)..."
    Write-Info "This may take 5–15 minutes on first build."
    python setup_env.py -md $MODEL_LOCAL -q $QUANT
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "setup_env.py failed (exit code $LASTEXITCODE)."
        Write-Warn "Make sure Visual Studio 2022 Build Tools (C++ workload) are installed."
        exit $LASTEXITCODE
    }
    Write-Ok "Build complete."
}

# Verify the binary exists
if (-not (Test-Path $LLAMA_CLI)) {
    # MSVC may produce the binary in a different location; search for it
    $found = Get-ChildItem -Recurse -Filter "llama-cli.exe" -ErrorAction SilentlyContinue |
             Select-Object -First 1 -ExpandProperty FullName
    if ($found) {
        Write-Warn "llama-cli.exe found at '$found' (not default path — update `$LLAMA_CLI if needed)."
        $LLAMA_CLI = $found
    }
    else {
        Write-Fail "llama-cli.exe not found after build. Check build output above."
        exit 1
    }
}

Write-Host ""

# ---------------------------------------------------------------------------
# Step 6: Smoke-test inference
# ---------------------------------------------------------------------------
Write-Info "Running smoke-test inference (50 tokens)..."
$smokePrompt = "Briefly describe what a 1-bit large language model is."
$smokeArgs   = @(
    "-m", $MODEL_GGUF,
    "-p", $smokePrompt,
    "-n", "50",
    "-t", "$NUM_THREADS",
    "--no-warmup"
)

Write-Host ""
Write-Host "--- Model output ---" -ForegroundColor DarkGray
& $LLAMA_CLI @smokeArgs
$exitCode = $LASTEXITCODE
Write-Host "--- End of output ---" -ForegroundColor DarkGray
Write-Host ""

if ($exitCode -ne 0) {
    Write-Fail "Smoke test failed (exit code $exitCode)."
    exit $exitCode
}

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  Setup complete!  BitNet is ready on Windows 11."        -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""
Write-Info "To start a multi-turn chat session, run:"
Write-Host "    python ..\windows\chat.py" -ForegroundColor Yellow
Write-Host ""
Write-Info "To check your CPU features (AVX2, AVX-512, AMX), run:"
Write-Host "    python ..\windows\check_cpu.py" -ForegroundColor Yellow
Write-Host ""
