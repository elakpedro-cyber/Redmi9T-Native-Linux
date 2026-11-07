param(
    [ValidateSet('v2','v2.1')][string]$Version = 'v2.1',
    [ValidateSet('C','B','A')][string]$Mode = 'C',
    [ValidateRange(10,3600)][int]$Seconds = 60,
    [ValidateSet('baseline','quiet')][string]$Profile = 'baseline',
    [switch]$CheckOnly,
    [switch]$TestActions,
    [switch]$Measure,
    [string]$KnownHosts
)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$nic = @(Get-CimInstance Win32_NetworkAdapter | Where-Object {
    $_.PNPDeviceID -like 'USB\VID_1D6B&PID_0106&MI_02*' -and $_.MACAddress -eq '02:00:00:00:77:01'
})
if ($nic.Count -ne 1) { throw 'Redmi USB NCM interface is absent or ambiguous' }
$console = @(Get-CimInstance Win32_SerialPort | Where-Object {
    $_.DeviceID -eq 'COM4' -and $_.PNPDeviceID -like 'USB\VID_1D6B&PID_0106&MI_00*'
})
if ($console.Count -ne 1) { throw 'The confirmed Redmi USB ACM COM4 interface is absent' }
$address = @(Get-NetIPAddress -InterfaceIndex $nic[0].InterfaceIndex -AddressFamily IPv4 | Where-Object {
    $_.IPAddress -eq '192.168.77.1' -and $_.PrefixLength -eq 30 -and $_.AddressState -eq 'Preferred'
})
if ($address.Count -ne 1) {
    throw 'USB NCM needs 192.168.77.1/30. Restore it with the existing administrator script.'
}
$action = if ($CheckOnly) { 'preflight' } else { 'start' }
$arguments = @((Join-Path $root "userspace/gnome-physical-$Version/control.py"), $action,
    '--mode', $Mode, '--seconds', "$Seconds", '--profile', $Profile)
if ($KnownHosts) { $arguments += @('--known-hosts', $KnownHosts) }
if ($Measure) {
    if ($Version -ne 'v2.1') { throw 'Copy instrumentation is available only in v2.1' }
    $arguments += '--measure'
}
if ($TestActions) { $arguments += '--test-actions' }
Push-Location $root
try {
    & python @arguments
    if ($LASTEXITCODE -ne 0) { throw "GNOME Physical controller exited $LASTEXITCODE" }
}
finally { Pop-Location }
