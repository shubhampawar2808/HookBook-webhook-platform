<#
.SYNOPSIS
  Tail HookForge launcher service logs.

.EXAMPLE
  .\scripts\dev-logs.ps1

.EXAMPLE
  .\scripts\dev-logs.ps1 -Service api -Tail 100
#>
[CmdletBinding()]
param(
    [ValidateSet("redis", "worker", "beat", "api", "receiver", "")]
    [string]$Service = "",
    [int]$Tail = 60
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib\DevLauncher.ps1")

Initialize-DevRuntime

$names = if ($Service) { @($Service) } else { $script:ServiceOrder }

if (-not $Service) {
    Write-Host "Available services: $($script:ServiceOrder -join ', ')"
    Write-Host "Usage: .\scripts\dev-logs.ps1 -Service api [-Tail 100]"
    Write-Host ""
}

foreach ($name in $names) {
    $logs = Get-LogPaths -Name $name
    Write-Host ("==== {0} stdout ({1}) ====" -f $name, $logs.Out) -ForegroundColor Cyan
    if (Test-Path $logs.Out) {
        Get-Content -Path $logs.Out -Tail $Tail
    }
    else {
        Write-Host "(no stdout log yet)"
    }
    Write-Host ("==== {0} stderr ({1}) ====" -f $name, $logs.Err) -ForegroundColor Yellow
    if (Test-Path $logs.Err) {
        Get-Content -Path $logs.Err -Tail $Tail
    }
    else {
        Write-Host "(no stderr log yet)"
    }
    Write-Host ""
}
