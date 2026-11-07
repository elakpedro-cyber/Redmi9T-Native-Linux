param(
    [switch]$Start,
    [string]$StopRun,
    [ValidateSet('480x720','720x1280','720x1600')][string]$Size = '480x720'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
    if ($StopRun) {
        $run = Get-Item -LiteralPath $StopRun
        $parent = (Get-Item -LiteralPath 'logs/v8b-gnome50-desktop').FullName
        if (!$run.PSIsContainer -or $run.Parent.FullName -ne $parent -or
            $run.Name -notmatch '^interactive-\d{8}T\d{9}$' -or
            ($run.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw 'Not a GNOME interactive run directory'
        }
        New-Item -ItemType File -Path (Join-Path $run.FullName 'stop.request') -Force | Out-Null
        return
    }
    $nic = & "$PSScriptRoot/Restore-LemonV8bUsbIp.ps1" | ConvertFrom-Json
    if (!($nic.Addresses | Where-Object { $_.IPAddress -eq '192.168.77.1' -and
        $_.PrefixLength -eq 30 -and $_.AddressState -eq 4 })) {
        throw 'USB NCM IP is unavailable. Use Restore-LemonV8bUsbIp.ps1 -Apply in a separate administrator shell.'
    }
    & ping.exe -n 1 -w 1000 192.168.77.2 | Out-Null
    if ($LASTEXITCODE) { throw 'Redmi did not answer on USB NCM' }
    wsl.exe --exec sh -c 'test -n "$DISPLAY" && command -v xfreerdp3 >/dev/null'
    if ($LASTEXITCODE) { throw 'WSLg or FreeRDP 3 is unavailable' }
    if (!$Start) { Write-Output 'USB NCM and the Windows RDP client are ready. Use -Start to begin an authorized session.'; return }
    $env:LEMON_RDP_RUN_LOG = "logs/v8b-gnome50-desktop/interactive-$(Get-Date -Format yyyyMMddTHHmmssfff)"
    $env:LEMON_RDP_DESKTOP = '1'
    $env:LEMON_RDP_CLIENT_MODE = 'interactive'
    $env:LEMON_RDP_SIZE = $Size
    $env:LEMON_RDP_SECONDS = '120'
    Write-Output "Session log: $env:LEMON_RDP_RUN_LOG"
    python -u logs/v8b-gnome50-rdp-hardware/controller.py
    if ($LASTEXITCODE) { throw "GNOME controller exited with code $LASTEXITCODE" }
}
finally { Pop-Location }

