<#
.SYNOPSIS
    Issue a locally-trusted TLS certificate for https://localhost development.

.DESCRIPTION
    Uses mkcert (https://github.com/FiloSottile/mkcert) to:
      1. Install a local Certificate Authority into the Windows + browser trust
         stores (so NO "NET::ERR_CERT_AUTHORITY_INVALID" warnings).
      2. Issue a leaf certificate valid for localhost / 127.0.0.1 / ::1.
    The cert + key are written to deploy/dev/certs/ where the dev nginx proxy
    (deploy/dev/docker-compose.https.yml) mounts them.

    mkcert is installed via winget or Chocolatey if not already present.

.EXAMPLE
    pwsh scripts/setup-dev-https.ps1
#>
[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"

# Resolve repo paths relative to this script (scripts/ -> repo root).
$RepoRoot = Split-Path -Parent $PSScriptRoot
$CertDir  = Join-Path $RepoRoot "deploy\dev\certs"
New-Item -ItemType Directory -Force -Path $CertDir | Out-Null

function Test-Command([string]$Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

# --- 1. Ensure mkcert is installed -----------------------------------------
if (-not (Test-Command mkcert)) {
    Write-Host "mkcert not found — attempting to install..." -ForegroundColor Yellow
    if (Test-Command winget) {
        winget install --id FiloSottile.mkcert -e --accept-source-agreements --accept-package-agreements
    } elseif (Test-Command choco) {
        choco install mkcert -y
    } else {
        throw "Neither winget nor choco is available. Install mkcert manually: https://github.com/FiloSottile/mkcert/releases then re-run."
    }
    # winget may not refresh PATH in the current session.
    if (-not (Test-Command mkcert)) {
        throw "mkcert installed but not on PATH for this session. Open a new terminal and re-run."
    }
}

# --- 2. Install the local CA into the trust store --------------------------
Write-Host "Installing mkcert local CA (you may be prompted to allow it)..." -ForegroundColor Cyan
mkcert -install

# --- 3. Issue the leaf certificate -----------------------------------------
Push-Location $CertDir
try {
    Write-Host "Issuing certificate for localhost / 127.0.0.1 / ::1 ..." -ForegroundColor Cyan
    mkcert -key-file localhost-key.pem -cert-file localhost.pem localhost 127.0.0.1 ::1
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Done. Dev certificate written to:" -ForegroundColor Green
Write-Host "  $((Join-Path $CertDir 'localhost.pem'))"
Write-Host "  $((Join-Path $CertDir 'localhost-key.pem'))"
Write-Host ""
Write-Host "Next:" -ForegroundColor Green
Write-Host "  1. In .env set:"
Write-Host "       NEXT_PUBLIC_API_BASE_URL=https://localhost/api"
Write-Host "       CSRF_TRUSTED_ORIGINS=https://localhost,http://localhost:3000"
Write-Host "  2. docker compose -f docker-compose.yml -f deploy/dev/docker-compose.https.yml up --build"
Write-Host "  3. Open https://localhost"
