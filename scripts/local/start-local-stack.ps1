param(
  [ValidateSet('both', 'dagster', 'dashboard', 'none')]
  [string]$Start = 'both',
  [int]$DagsterPort = 3000,
  [int]$DashboardPort = 3600,
  [int]$StartupTimeoutSec = 180,
  [switch]$InstallDashboardDeps
)

$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'stack-common.ps1')

# `dashboard/` is the canonical Nuxt app started by this launcher.
# The former `nuxt_dashboard/` tree was archived to `archive/nuxt_dashboard_legacy_20260306/` and is not booted here.

function Ensure-SeededJson {
  param(
    [string]$TargetPath,
    [string]$SeedPath
  )

  if (Test-Path $TargetPath) {
    return
  }
  if (-not (Test-Path $SeedPath)) {
    return
  }

  $targetDir = Split-Path -Parent $TargetPath
  if (-not (Test-Path $targetDir)) {
    New-Item -Path $targetDir -ItemType Directory -Force | Out-Null
  }

  Copy-Item -Path $SeedPath -Destination $TargetPath -Force
  Write-Host "Seeded runtime file: $TargetPath" -ForegroundColor DarkGray
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$dashboardDir = Join-Path $repoRoot 'dashboard'

Ensure-SeededJson -TargetPath (Join-Path $repoRoot 'dashboard\data\battery_state.json') -SeedPath (Join-Path $repoRoot 'dashboard\data\seeds\battery_state.seed.json')
Ensure-SeededJson -TargetPath (Join-Path $repoRoot 'energy_ml\configs\user_config.json') -SeedPath (Join-Path $repoRoot 'energy_ml\configs\templates\user_config.seed.json')
Ensure-SeededJson -TargetPath (Join-Path $repoRoot 'energy_ml\configs\recalculation_status.json') -SeedPath (Join-Path $repoRoot 'energy_ml\configs\templates\recalculation_status.seed.json')
Ensure-SeededJson -TargetPath (Join-Path $repoRoot 'energy_ml\configs\recalculation_trigger.json') -SeedPath (Join-Path $repoRoot 'energy_ml\configs\templates\recalculation_trigger.seed.json')
Ensure-SeededJson -TargetPath (Join-Path $repoRoot 'energy_ml\outputs\analytics_cache.json') -SeedPath (Join-Path $repoRoot 'energy_ml\outputs\templates\analytics_cache.seed.json')
Ensure-SeededJson -TargetPath (Join-Path $repoRoot 'energy_ml\outputs\latest_ml_results.json') -SeedPath (Join-Path $repoRoot 'energy_ml\outputs\templates\latest_ml_results.seed.json')
Ensure-SeededJson -TargetPath (Join-Path $repoRoot 'energy_ml\outputs\control_status.json') -SeedPath (Join-Path $repoRoot 'energy_ml\outputs\templates\control_status.seed.json')

Write-Host 'Smart Energy AI Local Stack Launcher' -ForegroundColor Cyan
Write-Host "Repo root: $repoRoot"
Write-Host "Requested start mode: $Start"

$dagsterUrl = "http://127.0.0.1:$DagsterPort/server_info"
$dashboardUrl = "http://127.0.0.1:$DashboardPort/api/health"

$shouldStartDagster = ($Start -eq 'both' -or $Start -eq 'dagster')
$shouldStartDashboard = ($Start -eq 'both' -or $Start -eq 'dashboard')

if ($shouldStartDagster) {
  if (Test-Endpoint -Url $dagsterUrl) {
    Write-Host "Dagster already reachable: $dagsterUrl" -ForegroundColor Green
  } else {
    $dagsterOwner = Get-ListeningPortProcessId -Port $DagsterPort
    if ($dagsterOwner) {
      Write-Host "Dagster port $DagsterPort already has a listener (PID $dagsterOwner); waiting for health endpoint before starting another process." -ForegroundColor Yellow
    } else {
      $dagsterPython = Resolve-DagsterPython -RepoRoot $repoRoot
      Write-Host "Using Dagster Python: $dagsterPython" -ForegroundColor Green

      $dagsterCommand = "Set-Location '$repoRoot'; & '$dagsterPython' -m dagster dev -h 127.0.0.1 -p $DagsterPort -d '$repoRoot' -m src.definitions"
      Start-Process -FilePath 'pwsh' -ArgumentList @('-NoExit', '-Command', $dagsterCommand) -WorkingDirectory $repoRoot | Out-Null
      Write-Host 'Started Dagster in a new PowerShell window.' -ForegroundColor Yellow
    }
  }
}

if ($shouldStartDashboard) {
  if (-not (Test-Path (Join-Path $dashboardDir 'node_modules'))) {
    if ($InstallDashboardDeps) {
      Write-Host 'Installing dashboard dependencies (node_modules missing)...' -ForegroundColor Yellow
      Push-Location $dashboardDir
      try {
        npm install --legacy-peer-deps
      } finally {
        Pop-Location
      }
    } else {
      throw "dashboard/node_modules is missing. Re-run with -InstallDashboardDeps to install dependencies first."
    }
  }

  if (Test-Endpoint -Url $dashboardUrl) {
    Write-Host "Dashboard API already reachable: $dashboardUrl" -ForegroundColor Green
  } else {
    $dashboardOwner = Get-ListeningPortProcessId -Port $DashboardPort
    if ($dashboardOwner) {
      Write-Host "Dashboard port $DashboardPort already has a listener (PID $dashboardOwner); waiting for health endpoint before starting another process." -ForegroundColor Yellow
    } else {
      $dashboardCommand = "Set-Location '$dashboardDir'; npm run dev"
      Start-Process -FilePath 'pwsh' -ArgumentList @('-NoExit', '-Command', $dashboardCommand) -WorkingDirectory $dashboardDir | Out-Null
      Write-Host 'Started dashboard dev server in a new PowerShell window.' -ForegroundColor Yellow
    }
  }
}

if ($Start -ne 'none') {
  if ($shouldStartDagster) {
    if (-not (Wait-Endpoint -Url $dagsterUrl -TimeoutSec $StartupTimeoutSec)) {
      throw "Dagster did not become healthy at $dagsterUrl within $StartupTimeoutSec seconds."
    }
    Write-Host "Dagster healthy: $dagsterUrl" -ForegroundColor Green
  }

  if ($shouldStartDashboard) {
    if (-not (Wait-Endpoint -Url $dashboardUrl -TimeoutSec $StartupTimeoutSec)) {
      throw "Dashboard API did not become healthy at $dashboardUrl within $StartupTimeoutSec seconds."
    }
    Write-Host "Dashboard healthy: $dashboardUrl" -ForegroundColor Green
  }
}

Write-Host 'Local stack check complete.' -ForegroundColor Cyan