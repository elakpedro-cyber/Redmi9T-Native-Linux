[CmdletBinding()]
param(
    [switch]$ConfigureIPv4,
    [switch]$TestSsh,
    [switch]$TestScp,
    [string]$ExpectedHostFingerprint,
    [string]$HostPublicKeyPath,
    [string]$IdentityFile = "$env:USERPROFILE\.ssh\id_ed25519",
    [switch]$InteractiveKey,
    [string]$SerialPort = 'COM4',
    [switch]$SkipSerialDiagnostics
)
$ErrorActionPreference = 'Stop'
$project = Split-Path $PSScriptRoot -Parent
$logDir = Join-Path $project ('logs\hardware-v7\' + (Get-Date -Format 'yyyyMMddTHHmmssfff'))
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$checks = [ordered]@{}
$status = 'INCOMPLETE'
function Get-HomeSnapshot {
    $homeAddresses = @(Get-NetIPAddress -AddressFamily IPv4 | Where-Object IPAddress -Like '192.168.0.*')
    $items = foreach ($item in $homeAddresses) {
        [ordered]@{
            Index = $item.InterfaceIndex
            Address = $item.IPAddress
            Prefix = $item.PrefixLength
            Dhcp = [string](Get-NetIPInterface -InterfaceIndex $item.InterfaceIndex -AddressFamily IPv4).Dhcp
            Dns = @((Get-DnsClientServerAddress -InterfaceIndex $item.InterfaceIndex -AddressFamily IPv4).ServerAddresses)
            Gateway = @((Get-NetRoute -InterfaceIndex $item.InterfaceIndex -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue).NextHop)
        }
    }
    @($items | Sort-Object Index,Address) | ConvertTo-Json -Depth 5 -Compress
}
function Invoke-LoggedNative([string]$Program,[string[]]$Arguments,[string]$Name) {
    & $Program @Arguments 2>&1 | Tee-Object -FilePath (Join-Path $logDir "$Name.txt") | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "$Name failed with exit code $LASTEXITCODE. See $logDir." }
}
$homeBefore = Get-HomeSnapshot
$homeBefore | Set-Content (Join-Path $logDir 'home-network-before.json')
try {
    if ($TestScp) { $TestSsh = $true }
    $baseArgs = @{ LogDirectory = (Join-Path $logDir 'usb'); IdentityFile = $IdentityFile }
    if ($ConfigureIPv4) { $baseArgs.ConfigureIPv4 = $true }
    if ($TestSsh) { $baseArgs.TestSsh = $true; $baseArgs.ExpectedHostFingerprint = $ExpectedHostFingerprint }
    if ($HostPublicKeyPath) { $baseArgs.HostPublicKeyPath = $HostPublicKeyPath }
    if ($InteractiveKey) { $baseArgs.InteractiveKey = $true }
    & (Join-Path $PSScriptRoot 'Test-LemonUsbV7.ps1') @baseArgs
    $checks.UsbAdapterWindowsIpRouteTcp = 'PASS'
    Invoke-LoggedNative 'ping.exe' @('-4','-S','192.168.77.1','-n','3','-w','2000','192.168.77.2') 'ping'
    $checks.PingPhone = 'PASS'
    if ($TestSsh) {
        $batch = if ($InteractiveKey) { 'no' } else { 'yes' }
        $common = @('-i',$IdentityFile,'-o','IdentitiesOnly=yes','-o',"BatchMode=$batch",'-o','KexAlgorithms=curve25519-sha256','-o','ConnectTimeout=10','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2','-o','PasswordAuthentication=no','-o','KbdInteractiveAuthentication=no','-o','PreferredAuthentications=publickey','-o','StrictHostKeyChecking=yes','-o',('UserKnownHostsFile=' + (Join-Path $logDir 'usb\known_hosts')))
        $readChecks = 'test "$(cat /run/init-reached)" = LEMON_INIT_V7_REACHED && test "$(cat /run/openrc-reached)" = LEMON_OPENRC_V7_REACHED && uname -a && cat /etc/alpine-release && rc-status && rc-service lemon-sshd status && ip -4 address show dev usb0 && cat /proc/mounts /proc/swaps && for d in /sys/block/sd*; do echo "$d"; cat "$d/stat" "$d/device/ioerr_cnt"; done'
        Invoke-LoggedNative 'ssh.exe' ($common + @('root@192.168.77.2',$readChecks)) 'ssh-system'
        Invoke-LoggedNative 'ssh.exe' ($common + @('root@192.168.77.2','ip -o -4 address show dev usb0 | grep -F "192.168.77.2/30"')) 'phone-ip'
        $storageCheck = 'for d in sda sdb sdc sdd sde sdf; do test -b /dev/$d || exit 30; /bin/busybox awk ''$5 != 0 || $7 != 0 || $12 != 0 || $14 != 0 {bad=1} END {exit bad}'' /sys/block/$d/stat || exit 31; done; /bin/busybox awk ''$3 !~ /^(rootfs|tmpfs|devtmpfs|proc|sysfs|devpts|configfs|pstore|cgroup|cgroup2)$/ {bad=1} END {exit bad}'' /proc/mounts || exit 32; test "$(wc -l < /proc/swaps)" -eq 1'
        Invoke-LoggedNative 'ssh.exe' ($common + @('root@192.168.77.2',$storageCheck)) 'storage-safety-before'
        $checks.SshUnameAlpineOpenRc = 'PASS'
        if ($TestScp) {
            # Refuse any transfer unless the exact destination filesystem is tmpfs.
            $tmpCheck = '/bin/busybox awk ''$2 == "/tmp" && $3 == "tmpfs" {ok=1} END {exit !ok}'' /proc/mounts'
            Invoke-LoggedNative 'ssh.exe' ($common + @('root@192.168.77.2',$tmpCheck)) 'verify-tmpfs'
            $id = [guid]::NewGuid().ToString('N')
            $local = Join-Path $logDir "payload-$id.bin"
            $remote = "/tmp/lemon-v7-$id.bin"
            $bytes = [byte[]]::new(1024)
            $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
            try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
            [IO.File]::WriteAllBytes($local,$bytes)
            Invoke-LoggedNative 'scp.exe' ($common + @($local,"root@192.168.77.2:$remote")) 'scp-upload'
            Invoke-LoggedNative 'ssh.exe' ($common + @('root@192.168.77.2',"/bin/busybox sha256sum $remote")) 'remote-sha256'
            $hash = (Get-FileHash -LiteralPath $local -Algorithm SHA256).Hash.ToLowerInvariant()
            $remoteHash = ((Get-Content (Join-Path $logDir 'remote-sha256.txt') -Raw).Trim() -split '\s+')[0]
            if ($remoteHash -ne $hash) { throw 'Uploaded file SHA-256 differs.' }
            $returned = Join-Path $logDir "returned-$id.bin"
            Invoke-LoggedNative 'scp.exe' ($common + @("root@192.168.77.2:$remote",$returned)) 'scp-download'
            if ((Get-FileHash -LiteralPath $returned -Algorithm SHA256).Hash.ToLowerInvariant() -ne $hash) { throw 'Downloaded file SHA-256 differs.' }
            $checks.ScpTmpfsRoundtrip = @{ Bytes = 1024; Sha256 = $hash; Status = 'PASS' }
            Invoke-LoggedNative 'ssh.exe' ($common + @('root@192.168.77.2',"/bin/busybox rm -f $remote")) 'remove-ram-test-file'
            Invoke-LoggedNative 'ssh.exe' ($common + @('root@192.168.77.2','for d in /sys/block/sd*; do echo "$d"; cat "$d/stat" "$d/device/ioerr_cnt"; done; cat /proc/mounts /proc/swaps')) 'storage-after-scp'
            Invoke-LoggedNative 'ssh.exe' ($common + @('root@192.168.77.2',$storageCheck)) 'storage-safety-after'
        }
    }
    $status = if ($TestScp) { 'NETWORK_SSH_SCP_COMMANDS_PASSED_REVIEW_STORAGE_LOGS' } elseif ($TestSsh) { 'NETWORK_SSH_PASSED_SCP_NOT_RUN' } else { 'NETWORK_ONLY_SSH_SCP_NOT_RUN' }
} catch {
    $status = 'FAILED'
    $_ | Out-String | Set-Content (Join-Path $logDir 'failure.txt')
    Write-Warning "Test failed: $($_.Exception.Message)"
    try {
        Get-PnpDevice -PresentOnly | Where-Object InstanceId -Match 'VID_1D6B' | Format-List * | Out-File (Join-Path $logDir 'failure-pnp.txt')
        $properties = foreach ($device in @(Get-PnpDevice -PresentOnly | Where-Object InstanceId -Match 'VID_1D6B')) {
            [ordered]@{ InstanceId=$device.InstanceId; Properties=@(Get-PnpDeviceProperty -InstanceId $device.InstanceId -ErrorAction SilentlyContinue | Select-Object KeyName,Type,Data) }
        }
        @($properties) | ConvertTo-Json -Depth 7 | Set-Content (Join-Path $logDir 'failure-pnp-properties.json')
        Get-CimInstance Win32_NetworkAdapter | Where-Object PNPDeviceID -Match 'VID_1D6B' | Format-List * | Out-File (Join-Path $logDir 'failure-adapters.txt')
        & ping.exe -4 -S 192.168.77.1 -n 2 -w 1000 192.168.77.2 2>&1 | Out-File (Join-Path $logDir 'failure-ping.txt')
    } catch { $_ | Out-String | Set-Content (Join-Path $logDir 'failure-host-diagnostics.txt') }
    if (-not $SkipSerialDiagnostics) {
        try {
            & python (Join-Path $PSScriptRoot 'collect-v7.py') --expect v7 --port $SerialPort 2>&1 | Out-File (Join-Path $logDir 'failure-serial-collector.txt')
            if ($LASTEXITCODE -ne 0) { Write-Warning 'Serial collection failed or port busy; no terminal was closed. See failure-serial-collector.txt.' }
        } catch { $_ | Out-String | Set-Content (Join-Path $logDir 'failure-serial-error.txt') }
    }
} finally {
    $homeAfter = Get-HomeSnapshot
    $homeAfter | Set-Content (Join-Path $logDir 'home-network-after.json')
    $homeUnchanged = $homeBefore -eq $homeAfter
    if (-not $homeUnchanged) { $status = 'FAILED_HOME_NETWORK_CHANGED'; Write-Warning 'Home network snapshot changed; no automatic restoration attempted.' }
    [ordered]@{ Status = $status; Checks = $checks; HomeNetworkUnchanged = $homeUnchanged; PhysicalUsbTest = $true; PhoneFlashOrRebootPerformed = $false } | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $logDir 'result.json')
    Write-Host "Logs: $logDir"
}
if ($status -like 'FAILED*') { throw "Hardware test failed; preserve ACM and inspect $logDir." }
