# Start HookForge Celery worker locally (Windows PowerShell)
# Uses Redis 3.0-compatible settings (remote control disabled).
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..\backend")

if (-not (Test-Path .\.venv)) {
  python -m venv .venv
}

.\.venv\Scripts\Activate.ps1
python ..\scripts\run_celery_worker_dev.py
