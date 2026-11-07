$ErrorActionPreference = 'Stop'
$project = Split-Path $PSScriptRoot -Parent
$global:LemonGuardWrites = 0
$results = @()
# Function mocks shadow cmdlets only inside this PowerShell process; no real network command is called.
function global:Get-PnpDevice {
    param($Class,[switch]$PresentOnly)
    [pscustomobject]@{ Status='OK'; FriendlyName='Mock ACM'; InstanceId='USB\VID_1D6B&PID_0106&MI_00' }
}
function global:Get-CimInstance {
    param($ClassName)
    if ($global:LemonGuardScenario -eq 'adapter-absent') { return }
    $mac = if ($global:LemonGuardScenario -eq 'wrong-mac') { 'AA:BB:CC:DD:EE:FF' } else { '02:00:00:00:77:01' }
    [pscustomobject]@{ PNPDeviceID='USB\VID_1D6B&PID_0106&MI_02'; MACAddress=$mac; InterfaceIndex=22 }
}
function global:Get-NetIPAddress {
    param($AddressFamily,$InterfaceIndex)
    [pscustomobject]@{ IPAddress='192.168.0.10'; InterfaceIndex=22; PrefixLength=24 }
}
function global:New-NetIPAddress {
    $global:LemonGuardWrites++
    throw 'Unexpected mutation in mock test'
}
function global:Get-NetAdapter { throw 'Unexpected adapter query after rejection guard' }
foreach ($scenario in @('adapter-absent','wrong-mac','protected-home-interface')) {
    $global:LemonGuardScenario = $scenario
    $expected = if ($scenario -eq 'protected-home-interface') { 'protected 192.168.0.x' } else { 'Expected one lemon NCM adapter' }
    $caught = $false
    try {
        & (Join-Path $PSScriptRoot 'Test-LemonUsbV6.ps1') -ConfigureIPv4 -LogDirectory (Join-Path $project "reports\v6-guard-mocks\$scenario")
    } catch {
        if (-not $_.Exception.Message.Contains($expected)) { throw }
        $caught = $true
    }
    if (-not $caught -or $global:LemonGuardWrites -ne 0) { throw "Guard failed: $scenario" }
    $results += [ordered]@{ Scenario=$scenario; Result='PASS'; NetworkMutations=0 }
}
[ordered]@{ Status='PASS'; Scope='Mocked rejection paths, not real USB/network'; Cases=$results } | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $project 'reports\v6-network-guard-tests.json')
Write-Host 'PASS: three guarded rejection scenarios, zero network mutations'
