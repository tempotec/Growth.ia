$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$logDir = Join-Path $repoRoot "logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$stdoutLog = Join-Path $logDir "sync-cache-$timestamp.log"
$stderrLog = Join-Path $logDir "sync-cache-$timestamp.err.log"

$env:PYTHONPATH = "."
python scripts\sync_bigquery_cache.py 1>> $stdoutLog 2>> $stderrLog
