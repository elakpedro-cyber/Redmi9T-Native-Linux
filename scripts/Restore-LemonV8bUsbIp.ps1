param([switch]$Apply)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$logs = Join-Path $root 'logs\v8b-usb-recovery'
$nic = @(Get-CimInstance Win32_NetworkAdapter | Where-Object {
    $_.PNPDeviceID -like 'USB\VID_1D6B&PID_0106&MI_02\*' -and $_.MACAddress -eq '02:00:00:00:77:01'
})
if ($nic.Count -ne 1) { throw 'NCM target absent or ambiguous' }
$index = [int]$nic[0].InterfaceIndex
$adapter = Get-NetAdapter -InterfaceIndex $index
$iface = Get-NetIPInterface -InterfaceIndex $index -AddressFamily IPv4
if ($adapter.Status -ne 'Up' -or $adapter.InterfaceDescription -ne 'UsbNcm Host Device' -or
    $iface.ConnectionState -ne 'Connected' -or $iface.Dhcp -ne 'Disabled') { throw 'Unexpected NCM state' }
$pnp = Get-PnpDevice -PresentOnly -InstanceId $nic[0].PNPDeviceID
if ($pnp.Status -ne 'OK') { throw 'NCM PnP error' }
$all = @(Get-NetIPAddress -AddressFamily IPv4)
$addresses = @($all | Where-Object InterfaceIndex -eq $index)
if (@($addresses | Where-Object { $_.IPAddress -notlike '169.254.*' -and $_.IPAddress -ne '192.168.77.1' }).Count) {
    throw 'Unexpected IPv4 already assigned to USB target'
}
if (@($all | Where-Object { $_.IPAddress -eq '192.168.77.1' -and $_.InterfaceIndex -ne $index }).Count) {
    throw '192.168.77.1 already exists on a different adapter'
}
$routes = @(Get-NetRoute -AddressFamily IPv4)
if (@($routes | Where-Object { $_.InterfaceIndex -ne $index -and $_.DestinationPrefix -in '192.168.77.0/30','192.168.77.2/32' }).Count) {
    throw 'Conflicting USB route on a different adapter'
}
$stamp = Get-Date -Format 'yyyyMMddTHHmmssfff'
$before = Join-Path $logs "windows-ip-preflight-$stamp.json"
[ordered]@{
    Target = $nic[0] | Select-Object InterfaceIndex,PNPDeviceID,MACAddress
    Addresses = $all | Select-Object InterfaceIndex,IPAddress,PrefixLength,PrefixOrigin,AddressState
    Routes = $routes | Select-Object InterfaceIndex,DestinationPrefix,NextHop,RouteMetric
    Dns = Get-DnsClientServerAddress -AddressFamily IPv4 | Select-Object InterfaceIndex,ServerAddresses
    TargetDhcp = [string]$iface.Dhcp
    Apply = [bool]$Apply
} | ConvertTo-Json -Depth 6 | Set-Content $before
$existing = @($addresses | Where-Object IPAddress -eq '192.168.77.1')
if ($existing.Count -and $existing[0].PrefixLength -ne 30) { throw 'Unexpected NCM prefix length' }
if ($Apply -and !$existing.Count) {
    New-NetIPAddress -InterfaceIndex $index -IPAddress '192.168.77.1' -PrefixLength 30 -PolicyStore ActiveStore | Out-Null
}
[ordered]@{
    Target = $nic[0].PNPDeviceID
    InterfaceIndex = $index
    Snapshot = $before
    Apply = [bool]$Apply
    Addresses = @(Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex $index | Select-Object IPAddress,PrefixLength,AddressState)
} | ConvertTo-Json -Depth 5 | Tee-Object (Join-Path $logs "windows-ip-result-$stamp.json")
