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
& $python (Join-Path $repo "nanoblock_scraper.py") --env-file $envFile 2>&1 |
    ForEach-Object { Write-Log "$_" }
$exitCode = $LASTEXITCODE
$ErrorActionPreference = $previous

Write-Log "Finished with exit code $exitCode"
exit $exitCode
