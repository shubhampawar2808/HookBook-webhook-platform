<#
.SYNOPSIS
  Show health of HookForge local development services.

.EXAMPLE
  .\scripts\dev-status.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Continue"
. (Join-Path $PSScriptRoot "lib\DevLauncher.ps1")

Initialize-DevRuntime
$registry = Get-DevRegistry

function Resolve-Pid {
    param([string]$Name)
    $entry = Get-ServiceEntry -Registry $registry -Name $Name
    if ($entry -and $entry.pid -and [int]$entry.pid -gt 0) {
        return [int]$entry.pid
    }
    $filePid = Read-PidFile -Name $Name
    if ($filePid) { return $filePid }
    return 0
}

function Status-Row {
    param($Name, $Status, $PidValue, $Port, $Detail)
    [pscustomobject]@{
        Name   = $Name
        Status = $Status
        Pid    = $(if ($PidValue) { "$PidValue" } else { "-" })
        Port   = $(if ($Port) { "$Port" } else { "-" })
        Detail = $Detail
    }
}

$rows = @()

# Redis
$redisPid = Resolve-Pid "redis"
$redisAlive = ($redisPid -gt 0) -and (Test-ProcessAlive -ProcessId $redisPid)
$redisPong = Test-RedisPong
$redisStatus = if ($redisPong) { "RUNNING" } elseif ($redisAlive) { "DEGRADED" } else { "STOPPED" }
$redisDetail = if ($redisPong) { "PONG" } elseif ((Test-PortListening -Port 6379)) { "port open, no PONG" } else { "down" }
$rows += Status-Row "Redis" $redisStatus $redisPid 6379 $redisDetail

# Worker
$workerPid = Resolve-Pid "worker"
$workerAlive = ($workerPid -gt 0) -and (Test-ProcessAlive -ProcessId $workerPid)
$workerStatus = if ($workerAlive) { "RUNNING" } else { "STOPPED" }
$workerDetail = if ($workerAlive) { "process alive (solo worker)" } else { "not tracked/alive" }
$rows += Status-Row "Worker" $workerStatus $workerPid "-" $workerDetail

# Beat
$beatPid = Resolve-Pid "beat"
$beatAlive = ($beatPid -gt 0) -and (Test-ProcessAlive -ProcessId $beatPid)
$beatStatus = if ($beatAlive) { "RUNNING" } else { "STOPPED" }
$beatDetail = if ($beatAlive) { "process alive" } else { "not tracked/alive" }
$rows += Status-Row "Beat" $beatStatus $beatPid "-" $beatDetail

# API
$apiPid = Resolve-Pid "api"
$apiAlive = ($apiPid -gt 0) -and (Test-ProcessAlive -ProcessId $apiPid)
$apiHealth = Test-HttpOk -Url "http://127.0.0.1:8000/health"
$apiStatus = if ($apiHealth) { "RUNNING" } elseif ($apiAlive) { "DEGRADED" } else { "STOPPED" }
$apiDetail = if ($apiHealth) { "GET /health OK" } elseif ((Test-PortListening -Port 8000)) { "port open, health fail" } else { "down" }
$rows += Status-Row "API" $apiStatus $apiPid 8000 $apiDetail

# Receiver
$recvPid = Resolve-Pid "receiver"
$recvAlive = ($recvPid -gt 0) -and (Test-ProcessAlive -ProcessId $recvPid)
$recvOk = Test-HttpOk -Url "http://127.0.0.1:9999/__status"
$recvStatus = if ($recvOk) { "RUNNING" } elseif ($recvAlive) { "DEGRADED" } else { "STOPPED" }
$recvDetail = if ($recvOk) { "GET /__status OK" } elseif ((Test-PortListening -Port 9999)) { "port open, status fail" } else { "down" }
$rows += Status-Row "Receiver" $recvStatus $recvPid 9999 $recvDetail

# Frontend (informational only — not managed)
$fe = Test-HttpOk -Url "http://127.0.0.1:5173" -TimeoutSec 1
$rows += Status-Row "Frontend" $(if ($fe) { "RUNNING" } else { "STOPPED" }) "-" 5173 $(if ($fe) { "responding" } else { "not managed by launcher" })

Write-Host ""
Write-Host "HOOKFORGE DEVELOPMENT STATUS" -ForegroundColor Cyan
Write-Host ("=" * 72)
Write-Host ("{0,-10} {1,-10} {2,-8} {3,-8} {4}" -f "SERVICE", "STATUS", "PID", "PORT", "CHECK")
Write-Host ("-" * 72)
foreach ($r in $rows) {
    $color = switch ($r.Status) {
        "RUNNING" { "Green" }
        "DEGRADED" { "Yellow" }
        default { "DarkGray" }
    }
    Write-Host ("{0,-10} {1,-10} {2,-8} {3,-8} {4}" -f $r.Name, $r.Status, $r.Pid, $r.Port, $r.Detail) -ForegroundColor $color
}
Write-Host ("=" * 72)

# DB identity reminder (no secrets)
try {
    Import-DotEnv
    $db = $env:DATABASE_URL
    if ($db -match '/hookforge_test(\?|$)') {
        Write-Host "WARNING: current process DATABASE_URL points at hookforge_test" -ForegroundColor Red
    }
    elseif ($db -match '/hookforge(\?|$)') {
        Write-Host "Configured app DB name: hookforge (from .env)" -ForegroundColor DarkGreen
    }
}
catch {
    Write-Host "Could not load .env for DB name check." -ForegroundColor Yellow
}

Write-Host "Registry: $($script:RegistryPath)"
Write-Host "Logs:     $($script:LogDir)"
exit 0
