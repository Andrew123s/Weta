# Start the API and the web dev server together (native processes, no containers).
# The job worker joins in Phase 2, when the jobs table exists.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\dev.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$api = Start-Process -FilePath "uv" -ArgumentList "run", "uvicorn", "weta_api.main:app", "--reload", "--port", "8000" -NoNewWindow -PassThru
try {
    pnpm --filter web dev
}
finally {
    if (-not $api.HasExited) { Stop-Process -Id $api.Id -Force }
}
