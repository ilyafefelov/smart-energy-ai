param(
  [ValidateSet('both', 'dagster', 'dashboard', 'none')]
  [string]$Start = 'both',
  [int]$DagsterPort = 3000,
  [int]$DashboardPort = 3600,
  [int]$StartupTimeoutSec = 90,
  [switch]$InstallDashboardDeps
)

$ErrorActionPreference = 'Stop'

# `dashboard/` is the canonical Nuxt app started by this launcher.
# The former `nuxt_dashboard/` tree was archived to `archive/nuxt_dashboard_legacy_20260306/` and is not booted here.

function Test-Endpoint {
  param(
    [string]$Url,
    [int]$TimeoutSec = 3
  )

  try {
    $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec
    return ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500)
  } catch {
    return $false
  }
}

function Wait-Endpoint {
  param(
    [string]$Url,
    [int]$TimeoutSec = 90
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSec)
  while ((Get-Date) -lt $deadline) {
    if (Test-Endpoint -Url $Url -TimeoutSec 3) {
      return $true
    }
    Start-Sleep -Seconds 2
  }

  return $false
}

function Test-PythonModule {
  param(
    [string]$PythonPath,
    [string]$ModuleName
  )

  if (-not (Test-Path $PythonPath)) {
    return $false
  }

  $result = & $PythonPath -c "import importlib.util; print('1' if importlib.util.find_spec('$ModuleName') else '0')" 2>$null
  return (($result -join '').Trim() -eq '1')
}

function Resolve-DagsterPython {
  param(
    [string]$RepoRoot
  )

  $candidates = @()
  $candidates += (Join-Path $RepoRoot '.venv\Scripts\python.exe')
  $candidates += (Join-Path $env:APPDATA 'pypoetry\venv\Scripts\python.exe')

  $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
  if ($pythonCmd -and $pythonCmd.Source) {
    $candidates += $pythonCmd.Source
  }

  foreach ($candidate in ($candidates | Select-Object -Unique)) {
    $hasDagster = Test-PythonModule -PythonPath $candidate -ModuleName 'dagster'
    $hasWebserver = Test-PythonModule -PythonPath $candidate -ModuleName 'dagster_webserver'
    if ($hasDagster -and $hasWebserver) {
      return $candidate
    }
  }

  throw 'Unable to find a Python executable with both dagster and dagster_webserver installed.'
}

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
Ensure-SeededJson -TargetPath (Join-Path $repoRoot 'energy_ml\energy_ml\outputs\control_status.json') -SeedPath (Join-Path $repoRoot 'energy_ml\energy_ml\outputs\templates\control_status.seed.json')

Write-Host 'Smart Energy AI Local Stack Launcher' -ForegroundColor Cyan
Write-Host "Repo root: $repoRoot"
Write-Host "Requested start mode: $Start"

$dagsterUrl = "http://127.0.0.1:$DagsterPort/server_info"
$dashboardUrl = "http://127.0.0.1:$DashboardPort/api/metrics/dashboard"

$shouldStartDagster = ($Start -eq 'both' -or $Start -eq 'dagster')
$shouldStartDashboard = ($Start -eq 'both' -or $Start -eq 'dashboard')

if ($shouldStartDagster) {
  if (Test-Endpoint -Url $dagsterUrl) {
    Write-Host "Dagster already reachable: $dagsterUrl" -ForegroundColor Green
  } else {
    $dagsterPython = Resolve-DagsterPython -RepoRoot $repoRoot
    Write-Host "Using Dagster Python: $dagsterPython" -ForegroundColor Green

    $dagsterCommand = "Set-Location '$repoRoot'; & '$dagsterPython' -m dagster dev -h 127.0.0.1 -p $DagsterPort -d '$repoRoot' -m src.definitions"
    Start-Process -FilePath 'pwsh' -ArgumentList @('-NoExit', '-Command', $dagsterCommand) -WorkingDirectory $repoRoot | Out-Null
    Write-Host 'Started Dagster in a new PowerShell window.' -ForegroundColor Yellow
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
    $dashboardCommand = "Set-Location '$dashboardDir'; npm run dev"
    Start-Process -FilePath 'pwsh' -ArgumentList @('-NoExit', '-Command', $dashboardCommand) -WorkingDirectory $dashboardDir | Out-Null
    Write-Host 'Started dashboard dev server in a new PowerShell window.' -ForegroundColor Yellow
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