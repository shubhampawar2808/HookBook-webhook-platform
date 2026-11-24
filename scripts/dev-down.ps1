<#
.SYNOPSIS
  Stop only HookForge services started/tracked by the local launcher.

.EXAMPLE
  .\scripts\dev-down.ps1

.EXAMPLE
  .\scripts\dev-down.ps1 -Service api
#>
[CmdletBinding()]
param(
    [ValidateSet("redis", "worker", "beat", "api", "receiver", "")]
    [string]$Service = ""
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib\DevLauncher.ps1")

Initialize-DevRuntime
$registry = Get-DevRegistry

Write-Host "HOOKFORGE DEV SHUTDOWN" -ForegroundColor Cyan
Write-Host "Stopping only launcher-tracked PIDs (PostgreSQL service is never touched)."
Write-Host ""

$targets = if ($Service) { @($Service) } else { $script:StopOrder }

foreach ($name in $targets) {
    Stop-TrackedService -Name $name -Registry $registry
    if ($registry.services -is [hashtable]) {
        if ($registry.services.ContainsKey($name)) {
            $null = $registry.services.Remove($name)
        }
    }
    elseif ($registry.services -and $registry.services.PSObject.Properties.Name -contains $name) {
        $registry.services.PSObject.Properties.Remove($name)
    }
}

# Normalize services to hashtable for save
if ($registry.services -isnot [hashtable]) {
    $map = @{}
    if ($registry.services) {
        foreach ($p in $registry.services.PSObject.Properties) {
            $map[$p.Name] = $p.Value
        }
    }
    $registry.services = $map
}

Save-DevRegistry -Registry $registry

# Remove empty/stale pid files for stopped set
foreach ($name in $targets) {
    Remove-PidFile -Name $name
}

Write-Host ""
Write-Host "Shutdown complete."
Write-Host "Untracked Redis/API processes (owned=false) were left running if present."
exit 0
