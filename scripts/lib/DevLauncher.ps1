# Shared HookForge local development launcher helpers (Windows PowerShell).
# Dot-source from scripts/dev-*.ps1. Never prints secrets.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:HookForgeRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$script:RunDir = Join-Path $script:HookForgeRoot ".run"
$script:PidDir = Join-Path $script:RunDir "pids"
$script:LogDir = Join-Path $script:RunDir "logs"
$script:RegistryPath = Join-Path $script:RunDir "registry.json"

$script:RedisServer = Join-Path $script:HookForgeRoot "tools\redis\bin\redis-server.exe"
$script:RedisCli = Join-Path $script:HookForgeRoot "tools\redis\bin\redis-cli.exe"
$script:RedisConf = Join-Path $script:HookForgeRoot "tools\redis\bin\redis.windows.conf"
$script:VenvPython = Join-Path $script:HookForgeRoot "backend\.venv\Scripts\python.exe"
$script:VenvCelery = Join-Path $script:HookForgeRoot "backend\.venv\Scripts\celery.exe"
$script:BackendDir = Join-Path $script:HookForgeRoot "backend"
$script:ReceiverScript = Join-Path $script:HookForgeRoot "scripts\local_webhook_receiver.py"
$script:WorkerWrapper = Join-Path $script:HookForgeRoot "scripts\run_celery_worker_dev.py"
$script:VerifyDbScript = Join-Path $script:HookForgeRoot "scripts\verify_db_identity.py"
$script:RunLogged = Join-Path $script:HookForgeRoot "scripts\run_logged.py"

$script:ServiceOrder = @("redis", "worker", "beat", "api", "receiver")
$script:StopOrder = @("receiver", "api", "beat", "worker", "redis")

function Initialize-DevRuntime {
    New-Item -ItemType Directory -Force -Path $script:PidDir | Out-Null
    New-Item -ItemType Directory -Force -Path $script:LogDir | Out-Null
}

function Get-DevRegistry {
    if (-not (Test-Path $script:RegistryPath)) {
        return [pscustomobject]@{
            version    = 1
            updated_at = $null
            services   = @{}
        }
    }
    $raw = Get-Content -Raw -Path $script:RegistryPath
    if ([string]::IsNullOrWhiteSpace($raw)) {
        return [pscustomobject]@{
            version    = 1
            updated_at = $null
            services   = @{}
        }
    }
    $obj = $raw | ConvertFrom-Json
    if (-not $obj.services) {
        $obj | Add-Member -NotePropertyName services -NotePropertyValue (@{}) -Force
    }
    return $obj
}

function Save-DevRegistry {
    param([Parameter(Mandatory = $true)]$Registry)
    Initialize-DevRuntime
    $Registry.updated_at = (Get-Date).ToUniversalTime().ToString("o")
    # ConvertTo-Json needs hashtable-friendly services
    $Registry | ConvertTo-Json -Depth 6 | Set-Content -Path $script:RegistryPath -Encoding UTF8
}

function Get-ServiceEntry {
    param(
        [Parameter(Mandatory = $true)]$Registry,
        [Parameter(Mandatory = $true)][string]$Name
    )
    $services = $Registry.services
    if ($null -eq $services) { return $null }
    if ($services -is [hashtable]) {
        if ($services.ContainsKey($Name)) { return $services[$Name] }
        return $null
    }
    $prop = $services.PSObject.Properties[$Name]
    if ($null -eq $prop) { return $null }
    return $prop.Value
}

function Set-ServiceEntry {
    param(
        [Parameter(Mandatory = $true)]$Registry,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)]$Entry
    )
    if ($Registry.services -isnot [hashtable]) {
        $map = @{}
        if ($Registry.services) {
            $Registry.services.PSObject.Properties | ForEach-Object {
                $map[$_.Name] = $_.Value
            }
        }
        $Registry.services = $map
    }
    $Registry.services[$Name] = $Entry
}

function Test-ProcessAlive {
    param([int]$ProcessId)
    if ($ProcessId -le 0) { return $false }
    try {
        $p = Get-Process -Id $ProcessId -ErrorAction Stop
        return $null -ne $p
    }
    catch {
        return $false
    }
}

function Write-PidFile {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][int]$ProcessId
    )
    Initialize-DevRuntime
    Set-Content -Path (Join-Path $script:PidDir "$Name.pid") -Value $ProcessId -Encoding ASCII
}

function Remove-PidFile {
    param([Parameter(Mandatory = $true)][string]$Name)
    $path = Join-Path $script:PidDir "$Name.pid"
    if (Test-Path $path) {
        Remove-Item -Force -Path $path -ErrorAction SilentlyContinue
    }
}

function Read-PidFile {
    param([Parameter(Mandatory = $true)][string]$Name)
    $path = Join-Path $script:PidDir "$Name.pid"
    if (-not (Test-Path $path)) { return $null }
    $raw = (Get-Content -Path $path -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ([string]::IsNullOrWhiteSpace($raw)) { return $null }
    $id = 0
    if ([int]::TryParse($raw.Trim(), [ref]$id)) { return $id }
    return $null
}

function Import-DotEnv {
    <#
    .SYNOPSIS
      Load KEY=VALUE pairs from repo .env into the current process environment.
      Does not print values. Skips comments and blank lines.
      Ensures DATABASE_URL comes from .env (not a leftover shell override to hookforge_test).
    #>
    $envFile = Join-Path $script:HookForgeRoot ".env"
    if (-not (Test-Path $envFile)) {
        throw ".env not found at $envFile"
    }

    # Drop shell overrides that could point API at the test database.
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:TEST_DATABASE_URL -ErrorAction SilentlyContinue

    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -eq "" -or $line.StartsWith("#")) { return }
        $eq = $line.IndexOf("=")
        if ($eq -lt 1) { return }
        $key = $line.Substring(0, $eq).Trim()
        $val = $line.Substring($eq + 1)
        if ($val.StartsWith('"') -and $val.EndsWith('"')) {
            $val = $val.Substring(1, $val.Length - 2)
        }
        Set-Item -Path "Env:$key" -Value $val
    }
}

function Assert-DevDatabaseIdentity {
    if (-not (Test-Path $script:VenvPython)) {
        throw "Backend venv python not found: $($script:VenvPython)"
    }
    $dbUrl = $env:DATABASE_URL
    if ([string]::IsNullOrWhiteSpace($dbUrl)) {
        throw "DATABASE_URL is not set after loading .env"
    }
    if ($dbUrl -match '/hookforge_test(\?|$)') {
        throw "REFUSING: DATABASE_URL points at hookforge_test. Normal development must use hookforge."
    }

    Push-Location $script:BackendDir
    try {
        $output = & $script:VenvPython $script:VerifyDbScript 2>&1
        $code = $LASTEXITCODE
        $text = ($output | Out-String)
        Write-Host $text.TrimEnd()
        if ($code -ne 0) {
            throw "Database identity check failed (exit $code). Expected hookforge / hookforge_app."
        }
        if ($text -notmatch "connected_db=hookforge\b") {
            throw "Database identity check did not confirm connected_db=hookforge."
        }
        if ($text -match "connected_db=hookforge_test") {
            throw "REFUSING: connected database is hookforge_test."
        }
    }
    finally {
        Pop-Location
    }
}

function Test-PortListening {
    param([Parameter(Mandatory = $true)][int]$Port)
    try {
        $c = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -First 1
        return $null -ne $c
    }
    catch {
        return $false
    }
}

function Test-RedisPong {
    if (-not (Test-Path $script:RedisCli)) { return $false }
    try {
        $result = & $script:RedisCli ping 2>$null
        return ($result -eq "PONG")
    }
    catch {
        return $false
    }
}

function Test-HttpOk {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [int]$TimeoutSec = 2
    )
    try {
        $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec
        return ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 300)
    }
    catch {
        return $false
    }
}

function Wait-Until {
    param(
        [Parameter(Mandatory = $true)][scriptblock]$Condition,
        [int]$TimeoutSec = 30,
        [int]$IntervalMs = 500,
        [string]$Label = "condition"
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (& $Condition) { return $true }
        Start-Sleep -Milliseconds $IntervalMs
    }
    Write-Host "TIMEOUT waiting for $Label" -ForegroundColor Yellow
    return $false
}

function Get-LogPaths {
    param([Parameter(Mandatory = $true)][string]$Name)
    Initialize-DevRuntime
    return @{
        Out = Join-Path $script:LogDir "$Name.out.log"
        Err = Join-Path $script:LogDir "$Name.err.log"
    }
}

function Start-TrackedProcess {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$ArgumentList = @(),
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [int]$Port = 0,
        [bool]$Owned = $true,
        [bool]$Direct = $false
    )

    $logs = Get-LogPaths -Name $Name
    "" | Set-Content -Path $logs.Out -Encoding UTF8
    "" | Set-Content -Path $logs.Err -Encoding UTF8

    # Prefer a logging wrapper so the launcher shell does not hold redirect pipes
    # (which can prevent PowerShell -File from exiting under job control).
    if ($Direct) {
        $exe = $FilePath
        $args = $ArgumentList
    }
    else {
        $exe = $script:VenvPython
        $args = @($script:RunLogged, $logs.Out, $logs.Err, $FilePath) + $ArgumentList
    }

    $proc = Start-Process -FilePath $exe -ArgumentList $args -WorkingDirectory $WorkingDirectory `
        -PassThru -WindowStyle Hidden
    if (-not $proc) {
        throw "Failed to start process for $Name"
    }

    Write-PidFile -Name $Name -ProcessId $proc.Id
    $entry = [pscustomobject]@{
        pid        = $proc.Id
        port       = $Port
        owned      = $Owned
        log_out    = $logs.Out
        log_err    = $logs.Err
        started_at = (Get-Date).ToUniversalTime().ToString("o")
        command    = "$FilePath $($ArgumentList -join ' ')"
        wrapper    = (-not $Direct)
    }
    return $entry
}

function Stop-TrackedService {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)]$Registry
    )
    $entry = Get-ServiceEntry -Registry $Registry -Name $Name
    $pidFromFile = Read-PidFile -Name $Name
    $targetPid = $null
    $owned = $true

    if ($entry) {
        $owned = [bool]$entry.owned
        if ($entry.pid) { $targetPid = [int]$entry.pid }
    }
    if (-not $targetPid -and $pidFromFile) {
        $targetPid = $pidFromFile
    }

    if (-not $owned) {
        Write-Host ("  {0,-10} SKIP (not owned by launcher)" -f $Name)
        Remove-PidFile -Name $Name
        return
    }

    if (-not $targetPid) {
        Write-Host ("  {0,-10} SKIP (no tracked PID)" -f $Name)
        Remove-PidFile -Name $Name
        return
    }

    if (-not (Test-ProcessAlive -ProcessId $targetPid)) {
        Write-Host ("  {0,-10} STALE pid={1} (already exited)" -f $Name, $targetPid)
        Remove-PidFile -Name $Name
        return
    }

    try {
        # /T terminates only this tracked PID tree (wrapper + child), never by image name.
        $null = & taskkill.exe /PID $targetPid /T /F 2>&1
        $null = Wait-Until -TimeoutSec 8 -IntervalMs 200 -Label "$Name stop" -Condition {
            -not (Test-ProcessAlive -ProcessId $targetPid)
        }
        if (Test-ProcessAlive -ProcessId $targetPid) {
            Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
        }
        Write-Host ("  {0,-10} STOPPED pid={1}" -f $Name, $targetPid)
    }
    catch {
        Write-Host ("  {0,-10} ERROR stopping pid={1}: {2}" -f $Name, $targetPid, $_.Exception.Message) -ForegroundColor Red
    }
    finally {
        Remove-PidFile -Name $Name
    }
}

function Get-TailText {
    param(
        [string]$Path,
        [int]$Lines = 40
    )
    if (-not $Path -or -not (Test-Path $Path)) { return "" }
    return (Get-Content -Path $Path -Tail $Lines -ErrorAction SilentlyContinue | Out-String)
}

function Show-ServiceDashboard {
    param(
        [Parameter(Mandatory = $true)]$Rows
    )
    Write-Host ""
    Write-Host "HOOKFORGE DEVELOPMENT ENVIRONMENT" -ForegroundColor Cyan
    Write-Host ("=" * 56)
    Write-Host ("{0,-10} {1,-10} {2,-8} {3,-8} {4}" -f "SERVICE", "STATUS", "PID", "PORT", "LOG")
    Write-Host ("-" * 56)
    foreach ($row in $Rows) {
        $color = if ($row.Status -eq "RUNNING") { "Green" } elseif ($row.Status -eq "FAILED") { "Red" } else { "Yellow" }
        Write-Host ("{0,-10} {1,-10} {2,-8} {3,-8} {4}" -f $row.Name, $row.Status, $row.Pid, $row.Port, $row.Log) -ForegroundColor $color
    }
    Write-Host ("=" * 56)
    Write-Host ""
    Write-Host "Frontend (start separately if needed):"
    Write-Host "  cd frontend; npm run dev"
    Write-Host "  http://localhost:5173"
    Write-Host ""
    Write-Host "Backend:   http://localhost:8000"
    Write-Host "API docs:  http://localhost:8000/docs"
    Write-Host "Receiver:  http://127.0.0.1:9999"
    Write-Host ""
    Write-Host "Commands:  .\scripts\dev-status.ps1 | .\scripts\dev-logs.ps1 -Service api | .\scripts\dev-down.ps1"
}

function Ensure-Prerequisites {
    $missing = @()
    if (-not (Test-Path $script:RedisServer)) { $missing += "portable Redis server ($($script:RedisServer))" }
    if (-not (Test-Path $script:RedisCli)) { $missing += "redis-cli" }
    if (-not (Test-Path $script:RedisConf)) { $missing += "redis.windows.conf" }
    if (-not (Test-Path $script:VenvPython)) { $missing += "backend .venv python" }
    if (-not (Test-Path $script:VenvCelery)) { $missing += "backend .venv celery" }
    if (-not (Test-Path $script:ReceiverScript)) { $missing += "local_webhook_receiver.py" }
    if (-not (Test-Path $script:WorkerWrapper)) { $missing += "run_celery_worker_dev.py" }
    if (-not (Test-Path $script:RunLogged)) { $missing += "run_logged.py" }
    if ($missing.Count -gt 0) {
        throw ("Missing prerequisites:`n - " + ($missing -join "`n - "))
    }
}
