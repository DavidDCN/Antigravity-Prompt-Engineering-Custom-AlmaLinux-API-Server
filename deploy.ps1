# One-command deploy script from Windows PowerShell to AlmaLinux VM (192.168.1.11)
# Usage: .\deploy.ps1
param(
    [string]$VmTarget = "daviddcn@192.168.1.11"
)

$ErrorActionPreference = "Stop"

# Automatically find scp.exe and ssh.exe even if OpenSSH/Git is not in PowerShell's PATH
$ScpCandidates = @(
    "C:\Windows\System32\OpenSSH\scp.exe",
    "C:\Program Files\Git\usr\bin\scp.exe"
)
$SshCandidates = @(
    "C:\Windows\System32\OpenSSH\ssh.exe",
    "C:\Program Files\Git\usr\bin\ssh.exe"
)

$ScpExe = $ScpCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
$SshExe = $SshCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $ScpExe -or -not $SshExe) {
    Write-Error "Could not find scp.exe or ssh.exe on this machine."
    exit 1
}

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "==> Step 1/2: Copying server/ and deploy/ to $VmTarget:~/attrial/ using $ScpExe ..." -ForegroundColor Cyan
& $ScpExe -r "$RepoRoot\server" "$RepoRoot\deploy" "${VmTarget}:~/attrial/"

Write-Host "==> Step 2/2: Running deploy/setup.sh on $VmTarget (syncing '/home/daviddcn/Downloads/background images' <-> SQLite DB)..." -ForegroundColor Cyan
& $SshExe -t $VmTarget "cd ~/attrial && sudo bash deploy/setup.sh"

Write-Host "==> Deployment complete! Refresh http://192.168.1.11/ in your browser and check your AlmaLinux 'Downloads/background images' folder!" -ForegroundColor Green
