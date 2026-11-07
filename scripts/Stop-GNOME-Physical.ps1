param(
    [ValidateSet('v2','v2.1')][string]$Version = 'v2.1',
    [switch]$Status,
    [string]$KnownHosts
)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$action = if ($Status) { 'status' } else { 'stop' }
$arguments = @((Join-Path $root "userspace/gnome-physical-$Version/control.py"), $action)
if ($KnownHosts) { $arguments += @('--known-hosts', $KnownHosts) }
Push-Location $root
try {
    & python @arguments
    if ($LASTEXITCODE -ne 0) { throw "GNOME Physical stop/status exited $LASTEXITCODE" }
}
finally { Pop-Location }
