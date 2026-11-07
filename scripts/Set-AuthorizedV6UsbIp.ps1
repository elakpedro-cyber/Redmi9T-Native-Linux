$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
$result=Join-Path $project 'logs\v6-authorized\windows-usb-ip-result.json'
try {
    $nic=@(Get-CimInstance Win32_NetworkAdapter | Where-Object { $_.PNPDeviceID -match 'VID_1D6B&PID_0106' -and $_.MACAddress -eq '02:00:00:00:77:01' })
    if ($nic.Count -ne 1) { throw 'Ambiguous or absent target USB NIC' }
    $index=[int]$nic[0].InterfaceIndex
    $protectedHomeIndexes=@(Get-NetIPAddress -AddressFamily IPv4 | Where-Object IPAddress -like '192.168.0.*' | Select-Object -ExpandProperty InterfaceIndex -Unique)
    if ($protectedHomeIndexes -contains $index) { throw 'Protected home network interface' }
    $conflicts=@(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -eq '192.168.77.1' -and $_.InterfaceIndex -ne $index })
    if ($conflicts.Count) { throw 'USB IP already exists on another interface' }
    $existing=@(Get-NetIPAddress -InterfaceIndex $index -AddressFamily IPv4 | Where-Object IPAddress -eq '192.168.77.1')
    if (-not $existing.Count) {
        New-NetIPAddress -InterfaceIndex $index -IPAddress 192.168.77.1 -PrefixLength 30 -PolicyStore ActiveStore | Out-Null
    } elseif ($existing[0].PrefixLength -ne 30) { throw 'Wrong existing USB prefix' }
    [ordered]@{Status='PASS';InterfaceIndex=$index;TargetPnp=$nic[0].PNPDeviceID;Addresses=@(Get-NetIPAddress -InterfaceIndex $index -AddressFamily IPv4 | Select-Object IPAddress,PrefixLength,AddressState);OtherInterfacesModified=$false} | ConvertTo-Json -Depth 5 | Set-Content $result
} catch {
    [ordered]@{Status='FAILED';Error=$_.Exception.Message} | ConvertTo-Json | Set-Content $result
    exit 1
}
