$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
$result=Join-Path $project 'logs\v6-authorized\client-key-unlock.json'
try {
    $before=Get-Service ssh-agent
    if ($before.Status -ne 'Running') { Start-Service ssh-agent }
    Write-Host 'Unlock the existing SSH client key here. Do not send its passphrase in chat.'
    & ssh-add.exe "$env:USERPROFILE\.ssh\id_ed25519"
    if ($LASTEXITCODE -ne 0) { throw 'ssh-add failed; no private key or passphrase is logged.' }
    $publicFingerprints=@(& ssh-add.exe -l)
    [ordered]@{Status='PASS';ServiceStatusBefore=[string]$before.Status;Fingerprints=$publicFingerprints;StartTypeChanged=$false} | ConvertTo-Json | Set-Content $result
    Write-Host 'Client key loaded. You can close this window.'
} catch {
    [ordered]@{Status='FAILED';Error=$_.Exception.Message} | ConvertTo-Json | Set-Content $result
    Write-Host $_.Exception.Message
}
Read-Host 'Press Enter to close'
