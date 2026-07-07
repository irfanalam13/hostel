# =============================================================================
# dev-up.ps1 — start the whole Hostel stack in one command (Windows/PowerShell)
#
#   ./scripts/dev-up.ps1            DEV: hot-reload stack (docker-compose.override.yml)
#   ./scripts/dev-up.ps1 -Prod      production-style stack (no reload, baked code)
#   ./scripts/dev-up.ps1 -Down      stop and remove all containers
#   ./scripts/dev-up.ps1 -NoLogs    start in the background without tailing logs
#   ./scripts/dev-up.ps1 -NoBuild   start without rebuilding images
#
# Runs postgres, redis, web (Django), celery_worker, celery_beat, frontend.
# In DEV (default) source is bind-mounted and servers auto-reload — no rebuild
# needed after code edits. In -Prod, code is baked in, so rebuild after changes.
# =============================================================================
[CmdletBinding()]
param(
    [switch]$Prod,
    [switch]$Down,
    [switch]$NoLogs,
    [switch]$NoBuild
)

$ErrorActionPreference = "Stop"

# Always run from the repo root (parent of this script's folder).
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

# -Prod pins to the base file only, so the dev override is NOT auto-merged.
$composeFiles = if ($Prod) { @("-f", "docker-compose.yml") } else { @() }

if ($Down) {
    Write-Host "Stopping all services..." -ForegroundColor Yellow
    docker compose @composeFiles down
    exit $LASTEXITCODE
}

if (-not (Test-Path ".env")) {
    Write-Warning ".env not found — copy .env.example to .env first."
    exit 1
}

$mode = if ($Prod) { "PROD (baked code, no reload)" } else { "DEV (hot reload)" }
$upArgs = @("compose") + $composeFiles + @("up", "-d")
if (-not $NoBuild) { $upArgs += "--build" }

Write-Host "Starting all services [$mode]: postgres, redis, web, celery_worker, celery_beat, frontend..." -ForegroundColor Cyan
docker @upArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

docker compose @composeFiles ps

$frontendPort = if ($env:FRONTEND_PORT) { $env:FRONTEND_PORT } else { "3000" }
$webPort      = if ($env:WEB_PORT)      { $env:WEB_PORT }      else { "8000" }

Write-Host ""
Write-Host "Frontend: http://localhost:$frontendPort" -ForegroundColor Green
Write-Host "Backend:  http://localhost:$webPort" -ForegroundColor Green

if (-not $NoLogs) {
    Write-Host ""
    Write-Host "Following logs (Ctrl-C to stop tailing; containers keep running)..." -ForegroundColor DarkGray
    docker compose @composeFiles logs -f
}
