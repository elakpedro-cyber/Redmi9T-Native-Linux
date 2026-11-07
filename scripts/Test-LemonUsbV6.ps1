[CmdletBinding()]
param(
    [switch]$ConfigureIPv4,
    [switch]$TestSsh,
    [string]$ExpectedHostFingerprint,
    [string]$HostPublicKeyPath,
    [string]$IdentityFile = "$env:USERPROFILE\.ssh\id_ed25519",
    [switch]$InteractiveKey,
    [string]$LogDirectory
)
$ErrorActionPreference = 'Stop'
$project = Split-Path $PSScriptRoot -Parent
$logDir = if ($LogDirectory) { $LogDirectory } else { Join-Path $project ('logs\windows-v6\' + (Get-Date -Format 'yyyyMMddTHHmmss')) }
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$ports = @(Get-PnpDevice -Class Ports -PresentOnly | Where-Object InstanceId -Match 'VID_1D6B&PID_010[46]')
$ports | Format-Table Status,FriendlyName,InstanceId | Out-String | Tee-Object -FilePath (Join-Path $logDir 'ports.txt') | Write-Host
if ($ports.Count -eq 0) { throw 'ACM port absent. Stop and collect USB diagnostics; do not disable or rebind the gadget.' }
$candidates = @(Get-CimInstance Win32_NetworkAdapter | Where-Object {
    $_.PNPDeviceID -match 'VID_1D6B&PID_0106' -and $_.MACAddress -eq '02:00:00:00:77:01'
})
if ($candidates.Count -ne 1) { throw "Expected one lemon NCM adapter, found $($candidates.Count). No network settings changed." }
$index = [int]$candidates[0].InterfaceIndex
$homeIndexes = @(Get-NetIPAddress -AddressFamily IPv4 | Where-Object IPAddress -Like '192.168.0.*' | Select-Object -ExpandProperty InterfaceIndex -Unique)
if ($homeIndexes -contains $index) { throw 'Refusing to configure an interface carrying the protected 192.168.0.x home network.' }
$adapter = Get-NetAdapter -InterfaceIndex $index
$adapter | Format-List Name,InterfaceIndex,InterfaceDescription,MacAddress,Status | Out-String | Tee-Object -FilePath (Join-Path $logDir 'adapter.txt') | Write-Host
if ($ConfigureIPv4) {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw '-ConfigureIPv4 requires an elevated PowerShell.' }
    $conflicts = @(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -eq '192.168.77.1' -and $_.InterfaceIndex -ne $index })
    if ($conflicts.Count) { throw '192.168.77.1 already exists on a different interface.' }
    $existing = @(Get-NetIPAddress -InterfaceIndex $index -AddressFamily IPv4 | Where-Object IPAddress -eq '192.168.77.1')
    if (-not $existing.Count) {
        New-NetIPAddress -InterfaceIndex $index -IPAddress 192.168.77.1 -PrefixLength 30 -PolicyStore ActiveStore | Out-Null
    } elseif ($existing[0].PrefixLength -ne 30) { throw 'Existing USB IPv4 has an unexpected prefix; no addresses removed.' }
}
Get-NetIPAddress -InterfaceIndex $index | Format-Table | Out-String | Tee-Object -FilePath (Join-Path $logDir 'addresses.txt') | Write-Host
$usbAddress = @(Get-NetIPAddress -InterfaceIndex $index -AddressFamily IPv4 | Where-Object { $_.IPAddress -eq '192.168.77.1' -and $_.PrefixLength -eq 30 })
if ($usbAddress.Count -ne 1) { throw 'USB Windows IPv4 must be 192.168.77.1/30; use -ConfigureIPv4 on the identified USB adapter.' }
for ($attempt = 0; $attempt -lt 10 -and $usbAddress[0].AddressState -ne 'Preferred'; $attempt++) {
    Start-Sleep -Seconds 1
    $usbAddress = @(Get-NetIPAddress -InterfaceIndex $index -AddressFamily IPv4 | Where-Object IPAddress -eq '192.168.77.1')
    if ($usbAddress.Count -ne 1) { throw 'USB IPv4 disappeared while waiting for duplicate-address detection.' }
}
if ($usbAddress[0].AddressState -ne 'Preferred') { throw 'USB IPv4 is not Preferred; check address conflict/DAD and adapter state.' }
$route = Find-NetRoute -RemoteIPAddress 192.168.77.2
if ($route.InterfaceIndex -notcontains $index) { throw 'Phone route does not use the validated USB interface. Configure its IPv4 first.' }
$tcp = Test-NetConnection -ComputerName 192.168.77.2 -Port 22 -InformationLevel Detailed
$tcp | Format-List | Out-String | Tee-Object -FilePath (Join-Path $logDir 'tcp22.txt') | Write-Host
if (-not $tcp.TcpTestSucceeded) { throw 'SSH port unavailable. Keep ACM open for read-only diagnostics.' }
if ($TestSsh) {
    if ($ExpectedHostFingerprint -notmatch '^SHA256:[A-Za-z0-9+/]+$') { throw 'Supply -ExpectedHostFingerprint read over the physical COM console for this boot.' }
    if (-not (Test-Path -LiteralPath $IdentityFile -PathType Leaf)) { throw 'SSH identity path does not exist.' }
    $known = Join-Path $logDir 'known_hosts'
    if ($HostPublicKeyPath) {
        $public = (Get-Content -LiteralPath $HostPublicKeyPath -Raw).Trim() -split '\s+'
        if ($public.Count -lt 2 -or $public[0] -ne 'ssh-ed25519') { throw 'Expected Ed25519 host public key obtained over COM.' }
        $scan = @('192.168.77.2 ' + $public[0] + ' ' + $public[1])
    } else {
        $scan = @(& ssh-keyscan.exe -T 5 -t ed25519 192.168.77.2 2>$null)
        if ($LASTEXITCODE -ne 0 -or -not $scan.Count) { throw 'Could not obtain SSH host public key; supply its COM-verified -HostPublicKeyPath.' }
    }
    [IO.File]::WriteAllLines($known, [string[]]$scan, [Text.UTF8Encoding]::new($false))
    $fingerprint = & ssh-keygen.exe -lf $known -E sha256
    if ($LASTEXITCODE -ne 0 -or ($fingerprint -split '\s+')[1] -ne $ExpectedHostFingerprint) { throw 'Host key mismatch: SSH authentication was not attempted.' }
    $batch = if ($InteractiveKey) { 'no' } else { 'yes' }
    & ssh.exe -i $IdentityFile -o IdentitiesOnly=yes -o "BatchMode=$batch" -o KexAlgorithms=curve25519-sha256 -o ConnectTimeout=10 -o ServerAliveInterval=5 -o ServerAliveCountMax=2 -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no -o PreferredAuthentications=publickey -o StrictHostKeyChecking=yes -o "UserKnownHostsFile=$known" root@192.168.77.2 'test "$(cat /run/init-reached)" = LEMON_INIT_V6_REACHED && test "$(cat /run/openrc-reached)" = LEMON_OPENRC_V6_REACHED && uname -r && cat /etc/alpine-release && apk --version && cat /proc/mounts /proc/swaps'
    if ($LASTEXITCODE -ne 0) { throw 'SSH command failed. For an encrypted key unlock your agent or use -InteractiveKey for its local passphrase.' }
}
Write-Host "Checks complete. Logs: $logDir"
