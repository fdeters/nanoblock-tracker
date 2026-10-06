# Runs the Nanoblock sync from Windows Task Scheduler.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_sync.ps1
$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$python = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Error "Virtual environment not found at $python. Run: py -3.11 -m venv .venv"
    exit 1
}

$logDir = Join-Path $repo "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir ("sync-{0}.log" -f (Get-Date -Format "yyyy-MM"))

function Write-Log([string]$message) {
    "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $message |
        Out-File -FilePath $logFile -Append -Encoding utf8
}

Write-Log "Starting sync"
$envFile = Join-Path $repo ".env"
$previous = $ErrorActionPreference
$ErrorActionPreference = "Continue"

# Update step: failures are logged but never block the sync itself.
$requirements = Join-Path $repo "requirements.txt"
$hashFile = Join-Path $repo ".venv\requirements.sha256"
if (Get-Command git -ErrorAction SilentlyContinue) {
    git -C $repo pull --ff-only 2>&1 | ForEach-Object { Write-Log "git: $_" }
    if ($LASTEXITCODE -ne 0) {
        Write-Log "git pull failed (exit code $LASTEXITCODE); continuing with the current checkout"
    }
} else {
    Write-Log "git not found on PATH; skipping git pull"
}

$currentHash = (Get-FileHash -Algorithm SHA256 $requirements).Hash
$installedHash = if (Test-Path $hashFile) { (Get-Content $hashFile -Raw).Trim() } else { "" }
if ($currentHash -ne $installedHash) {
    Write-Log "requirements.txt changed; installing dependencies"
    & $python -m pip install --disable-pip-version-check -r $requirements 2>&1 |
        ForEach-Object { Write-Log "pip: $_" }
    if ($LASTEXITCODE -eq 0) {
        Set-Content -Path $hashFile -Value $currentHash
    } else {
        Write-Log "pip install failed (exit code $LASTEXITCODE); continuing"
    }
}

& $python -c "import sys; from nanoblock_tracker.config import load_environment_config, resolve_config_value; load_environment_config(sys.argv[1]); sys.exit(0 if resolve_config_value(None, 'GOOGLE_SHEET_ID') else 1)" $envFile 2>&1 |
    ForEach-Object { Write-Log "config: $_" }
if ($LASTEXITCODE -ne 0) {
    Write-Log "GOOGLE_SHEET_ID is missing or empty; refusing to run a CSV-only export"
    exit 1
}

& $python (Join-Path $repo "nanoblock_scraper.py") --env-file $envFile --challenge-timeout 120 2>&1 |
    ForEach-Object { Write-Log "$_" }
$exitCode = $LASTEXITCODE
$ErrorActionPreference = $previous

Write-Log "Finished with exit code $exitCode"
exit $exitCode
