# Start Ragnar WhatsApp Odoo stack (Docker Compose)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    $dockerBin = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
    if (Test-Path $dockerBin) { $env:Path = "$(Split-Path $dockerBin);$env:Path" }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is not installed or not in PATH. See docs/DOCKER.md"
}

docker info 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Error @"
Docker daemon is not running.

Common fixes on Windows:
  1. Reboot after WSL install
  2. Enable virtualization in BIOS (VT-x/AMD-V)
  3. Start Docker Desktop manually

Then run: docker compose up --build -d
See docs/DOCKER.md
"@
}

Write-Host "Building and starting Odoo 17 + PostgreSQL..."
docker compose up --build -d

Write-Host ""
Write-Host "Waiting for Odoo (first run may take 2-5 min to init DB)..."
$ready = $false
for ($i = 0; $i -lt 90; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8069/web/login" -UseBasicParsing -TimeoutSec 5
        if ($r.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 5
    }
}

if ($ready) {
    Write-Host ""
    Write-Host "Odoo is ready:"
    Write-Host "  URL:      http://localhost:8069"
    Write-Host "  Database: ragnar"
    Write-Host "  Login:    admin"
    Write-Host "  Password: admin"
    Write-Host ""
    Write-Host "Open WhatsApp Bot menu after login."
} else {
    Write-Host "Odoo still starting. Check logs: docker compose logs -f odoo"
}
