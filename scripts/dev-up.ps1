<#
.SYNOPSIS
  Start the HookForge local development stack (Redis, Celery worker/beat, API, receiver).

.EXAMPLE
  .\scripts\dev-up.ps1

.EXAMPLE
  .\scripts\dev-up.ps1 -Service worker
#>
[CmdletBinding()]
param(
    [ValidateSet("redis", "worker", "beat", "api", "receiver", "")]
    [string]$Service = "",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib\DevLauncher.ps1")

Initialize-DevRuntime
Ensure-Prerequisites
Import-DotEnv
Assert-DevDatabaseIdentity

$registry = Get-DevRegistry
$startedThisRun = New-Object System.Collections.Generic.List[string]
$dashboard = New-Object System.Collections.Generic.List[object]
$failed = $false
$failReason = ""

function Add-Dash {
    param($Name, $Status, $PidValue, $Port, $Log)
    $dashboard.Add([pscustomobject]@{
            Name   = $Name
            Status = $Status
            Pid    = $(if ($PidValue) { $PidValue } else { "-" })
            Port   = $(if ($Port) { $Port } else { "-" })
            Log    = $(if ($Log) { Split-Path $Log -Leaf } else { "-" })
        }) | Out-Null
}

function Get-TrackedAliveEntry {
    param([string]$Name)
    $entry = Get-ServiceEntry -Registry $registry -Name $Name
    if ($entry -and $entry.pid -and (Test-ProcessAlive -ProcessId ([int]$entry.pid))) {
        return $entry
    }
    $filePid = Read-PidFile -Name $Name
    if ($filePid -and (Test-ProcessAlive -ProcessId $filePid)) {
        return [pscustomobject]@{ pid = $filePid; owned = $true; port = 0; log_err = (Get-LogPaths $Name).Err }
    }
    return $null
}

function Start-RedisService {
    $existing = Get-TrackedAliveEntry -Name "redis"
    if ($existing -and -not $Force) {
        if (Test-RedisPong) {
            Write-Host "Redis already tracked and healthy (pid=$($existing.pid))."
            Add-Dash "Redis" "RUNNING" $existing.pid 6379 $existing.log_err
            return
        }
    }

    if (Test-RedisPong) {
        Write-Host "Redis already responding on :6379 (external/untracked). Will not start a second instance."
        $entry = [pscustomobject]@{
            pid        = 0
            port       = 6379
            owned      = $false
            log_out    = $null
            log_err    = $null
            started_at = (Get-Date).ToUniversalTime().ToString("o")
            command    = "external"
        }
        Set-ServiceEntry -Registry $registry -Name "redis" -Entry $entry
        Add-Dash "Redis" "RUNNING" "-" 6379 "-"
        return
    }

    if (Test-PortListening -Port 6379) {
        throw "Port 6379 is in use but Redis PING failed. Resolve the conflict before starting."
    }

    Write-Host "Starting Redis..."
    $entry = Start-TrackedProcess -Name "redis" -FilePath $script:RedisServer `
        -ArgumentList @($script:RedisConf) `
        -WorkingDirectory (Split-Path $script:RedisServer -Parent) `
        -Port 6379 -Owned $true
    $startedThisRun.Add("redis") | Out-Null
    Set-ServiceEntry -Registry $registry -Name "redis" -Entry $entry

    $ok = Wait-Until -TimeoutSec 15 -Label "Redis PONG" -Condition { Test-RedisPong }
    if (-not $ok) {
        $tail = Get-TailText -Path $entry.log_err -Lines 30
        throw "Redis failed to become ready.`n$tail"
    }
    Add-Dash "Redis" "RUNNING" $entry.pid 6379 $entry.log_err
}

function Find-ProcessByCommand {
    param([string]$Pattern)
    try {
        return Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -and ($_.CommandLine -match $Pattern) } |
            Select-Object -First 1
    }
    catch {
        return $null
    }
}

function Start-WorkerService {
    if (-not (Test-RedisPong)) { throw "Redis is not healthy; cannot start Celery worker." }

    $existing = Get-TrackedAliveEntry -Name "worker"
    if ($existing -and -not $Force) {
        Write-Host "Celery worker already running (pid=$($existing.pid))."
        Add-Dash "Worker" "RUNNING" $existing.pid "-" $existing.log_err
        return
    }

    $orphan = Find-ProcessByCommand -Pattern "run_celery_worker_dev\.py"
    if ($orphan -and -not $Force) {
        Write-Host "Celery worker already running outside registry (pid=$($orphan.ProcessId)). Skipping new instance."
        $entry = [pscustomobject]@{
            pid = [int]$orphan.ProcessId; port = 0; owned = $false
            log_out = $null; log_err = $null
            started_at = (Get-Date).ToUniversalTime().ToString("o"); command = "external"
        }
        Set-ServiceEntry -Registry $registry -Name "worker" -Entry $entry
        Add-Dash "Worker" "RUNNING" $orphan.ProcessId "-" "-"
        return
    }

    Write-Host "Starting Celery worker (solo, remote-control disabled)..."
    $entry = Start-TrackedProcess -Name "worker" -FilePath $script:VenvPython `
        -ArgumentList @($script:WorkerWrapper) `
        -WorkingDirectory $script:BackendDir -Owned $true
    $startedThisRun.Add("worker") | Out-Null
    Set-ServiceEntry -Registry $registry -Name "worker" -Entry $entry

    $ok = Wait-Until -TimeoutSec 25 -Label "Celery worker ready" -Condition {
        if (-not (Test-ProcessAlive -ProcessId ([int]$entry.pid))) { return $false }
        $combined = (Get-TailText -Path $entry.log_out -Lines 80) + (Get-TailText -Path $entry.log_err -Lines 80)
        return ($combined -match "ready\.")
    }
    if (-not $ok -or -not (Test-ProcessAlive -ProcessId ([int]$entry.pid))) {
        $tail = (Get-TailText -Path $entry.log_err -Lines 40) + (Get-TailText -Path $entry.log_out -Lines 40)
        throw "Celery worker failed to start.`n$tail"
    }
    Add-Dash "Worker" "RUNNING" $entry.pid "-" $entry.log_err
}

function Start-BeatService {
    if (-not (Test-RedisPong)) { throw "Redis is not healthy; cannot start Celery Beat." }

    $existing = Get-TrackedAliveEntry -Name "beat"
    if ($existing -and -not $Force) {
        Write-Host "Celery Beat already running (pid=$($existing.pid))."
        Add-Dash "Beat" "RUNNING" $existing.pid "-" $existing.log_err
        return
    }

    $orphan = Find-ProcessByCommand -Pattern "celery_app\.celery_app beat"
    if ($orphan -and -not $Force) {
        Write-Host "Celery Beat already running outside registry (pid=$($orphan.ProcessId)). Skipping new instance."
        $entry = [pscustomobject]@{
            pid = [int]$orphan.ProcessId; port = 0; owned = $false
            log_out = $null; log_err = $null
            started_at = (Get-Date).ToUniversalTime().ToString("o"); command = "external"
        }
        Set-ServiceEntry -Registry $registry -Name "beat" -Entry $entry
        Add-Dash "Beat" "RUNNING" $orphan.ProcessId "-" "-"
        return
    }

    Write-Host "Starting Celery Beat..."
    $entry = Start-TrackedProcess -Name "beat" -FilePath $script:VenvCelery `
        -ArgumentList @("-A", "app.workers.celery_app.celery_app", "beat", "--loglevel=INFO") `
        -WorkingDirectory $script:BackendDir -Owned $true
    $startedThisRun.Add("beat") | Out-Null
    Set-ServiceEntry -Registry $registry -Name "beat" -Entry $entry

    $ok = Wait-Until -TimeoutSec 20 -Label "Celery Beat start" -Condition {
        if (-not (Test-ProcessAlive -ProcessId ([int]$entry.pid))) { return $false }
        $combined = (Get-TailText -Path $entry.log_out -Lines 80) + (Get-TailText -Path $entry.log_err -Lines 80)
        return ($combined -match "beat: Starting")
    }
    if (-not $ok -or -not (Test-ProcessAlive -ProcessId ([int]$entry.pid))) {
        $tail = (Get-TailText -Path $entry.log_err -Lines 40) + (Get-TailText -Path $entry.log_out -Lines 40)
        throw "Celery Beat failed to start.`n$tail"
    }
    Add-Dash "Beat" "RUNNING" $entry.pid "-" $entry.log_err
}

function Start-ApiService {
    Assert-DevDatabaseIdentity

    $existing = Get-TrackedAliveEntry -Name "api"
    if ($existing -and -not $Force) {
        if (Test-HttpOk -Url "http://127.0.0.1:8000/health") {
            Write-Host "FastAPI already running and healthy (pid=$($existing.pid))."
            Add-Dash "API" "RUNNING" $existing.pid 8000 $existing.log_err
            return
        }
    }

    if ((Test-PortListening -Port 8000) -and -not $Force) {
        if (Test-HttpOk -Url "http://127.0.0.1:8000/health") {
            Write-Host "FastAPI already healthy on :8000 (external/untracked)."
            $entry = [pscustomobject]@{
                pid = 0; port = 8000; owned = $false; log_out = $null; log_err = $null
                started_at = (Get-Date).ToUniversalTime().ToString("o"); command = "external"
            }
            Set-ServiceEntry -Registry $registry -Name "api" -Entry $entry
            Add-Dash "API" "RUNNING" "-" 8000 "-"
            return
        }
        throw "Port 8000 is in use but /health failed."
    }

    Write-Host "Starting FastAPI (DATABASE_URL -> hookforge)..."
    $entry = Start-TrackedProcess -Name "api" -FilePath $script:VenvPython `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000") `
        -WorkingDirectory $script:BackendDir -Port 8000 -Owned $true
    $startedThisRun.Add("api") | Out-Null
    Set-ServiceEntry -Registry $registry -Name "api" -Entry $entry

    $ok = Wait-Until -TimeoutSec 30 -Label "API /health" -Condition {
        (Test-ProcessAlive -ProcessId ([int]$entry.pid)) -and (Test-HttpOk -Url "http://127.0.0.1:8000/health")
    }
    if (-not $ok) {
        $tail = (Get-TailText -Path $entry.log_err -Lines 50) + (Get-TailText -Path $entry.log_out -Lines 50)
        throw "FastAPI failed readiness check.`n$tail"
    }
    Add-Dash "API" "RUNNING" $entry.pid 8000 $entry.log_err
}

function Start-ReceiverService {
    $existing = Get-TrackedAliveEntry -Name "receiver"
    if ($existing -and -not $Force) {
        if (Test-HttpOk -Url "http://127.0.0.1:9999/__status") {
            Write-Host "Webhook receiver already running (pid=$($existing.pid))."
            Add-Dash "Receiver" "RUNNING" $existing.pid 9999 $existing.log_err
            return
        }
    }

    if ((Test-PortListening -Port 9999) -and -not $Force) {
        if (Test-HttpOk -Url "http://127.0.0.1:9999/__status") {
            Write-Host "Receiver already healthy on :9999 (external/untracked)."
            $entry = [pscustomobject]@{
                pid = 0; port = 9999; owned = $false; log_out = $null; log_err = $null
                started_at = (Get-Date).ToUniversalTime().ToString("o"); command = "external"
            }
            Set-ServiceEntry -Registry $registry -Name "receiver" -Entry $entry
            Add-Dash "Receiver" "RUNNING" "-" 9999 "-"
            return
        }
        throw "Port 9999 is in use but /__status failed."
    }

    Write-Host "Starting local webhook receiver..."
    $entry = Start-TrackedProcess -Name "receiver" -FilePath $script:VenvPython `
        -ArgumentList @($script:ReceiverScript) `
        -WorkingDirectory $script:HookForgeRoot -Port 9999 -Owned $true
    $startedThisRun.Add("receiver") | Out-Null
    Set-ServiceEntry -Registry $registry -Name "receiver" -Entry $entry

    $ok = Wait-Until -TimeoutSec 15 -Label "receiver /__status" -Condition {
        (Test-ProcessAlive -ProcessId ([int]$entry.pid)) -and (Test-HttpOk -Url "http://127.0.0.1:9999/__status")
    }
    if (-not $ok) {
        $tail = (Get-TailText -Path $entry.log_err -Lines 40) + (Get-TailText -Path $entry.log_out -Lines 40)
        throw "Webhook receiver failed readiness check.`n$tail"
    }
    Add-Dash "Receiver" "RUNNING" $entry.pid 9999 $entry.log_err
}

$targets = if ($Service) { @($Service) } else { $script:ServiceOrder }

try {
    foreach ($name in $targets) {
        switch ($name) {
            "redis" { Start-RedisService }
            "worker" { Start-WorkerService }
            "beat" { Start-BeatService }
            "api" { Start-ApiService }
            "receiver" { Start-ReceiverService }
        }
    }
}
catch {
    $failed = $true
    $failReason = $_.Exception.Message
    Write-Host "`nSTARTUP FAILED: $failReason" -ForegroundColor Red
    Write-Host "Rolling back services started in this run..." -ForegroundColor Yellow
    foreach ($name in $script:StopOrder) {
        if ($startedThisRun -contains $name) {
            Stop-TrackedService -Name $name -Registry $registry
            if ($registry.services -is [hashtable] -and $registry.services.ContainsKey($name)) {
                $null = $registry.services.Remove($name)
            }
        }
    }
}

Save-DevRegistry -Registry $registry

if ($failed) {
    if ($dashboard.Count -gt 0) {
        Show-ServiceDashboard -Rows $dashboard
    }
    exit 1
}

# If single-service start, refresh dashboard for all known services via status-like checks
if ($Service) {
    # keep only the rows we added; still show summary
    Show-ServiceDashboard -Rows $dashboard
}
else {
    Show-ServiceDashboard -Rows $dashboard
}

# Frontend is NOT started by this launcher
Write-Host "Note: Frontend is not managed by dev-up. Start it with: cd frontend; npm run dev" -ForegroundColor DarkYellow
exit 0
